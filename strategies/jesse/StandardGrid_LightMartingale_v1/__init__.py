try:
    from strategies.StandardGrid_v1 import StandardGrid_v1
except ModuleNotFoundError:  # pragma: no cover
    from strategies.jesse.StandardGrid_v1 import StandardGrid_v1

from strategies.shared.standard_grid import next_buy_level_index, should_release_stale_slice, total_notional_cap_reached


class StandardGrid_LightMartingale_v1(StandardGrid_v1):
    def hyperparameters(self):
        defaults = {
            "base_level_notional_pct": 3,
            "level_size_multiplier": 1.35,
            "inventory_release_bars": 96,
            "inventory_release_buffer_pct": 5,
            "entry_box_break_bars": 3,
            "entry_box_break_buffer_pct": 2,
        }
        values = list(super().hyperparameters())
        values.append({"name": "base_level_notional_pct", "type": int, "min": 1, "max": 20, "default": defaults["base_level_notional_pct"]})
        values.append({"name": "level_size_multiplier", "type": float, "min": 1.1, "max": 2.0, "default": defaults["level_size_multiplier"]})
        values.append({"name": "inventory_release_bars", "type": int, "min": 12, "max": 500, "default": defaults["inventory_release_bars"]})
        values.append({"name": "inventory_release_buffer_pct", "type": int, "min": 1, "max": 20, "default": defaults["inventory_release_buffer_pct"]})
        values.append({"name": "entry_box_break_bars", "type": int, "min": 1, "max": 10, "default": defaults["entry_box_break_bars"]})
        values.append({"name": "entry_box_break_buffer_pct", "type": int, "min": 1, "max": 10, "default": defaults["entry_box_break_buffer_pct"]})
        return values

    @property
    def inventory_release_buffer(self):
        return self.hp["inventory_release_buffer_pct"] / 10

    @property
    def entry_box_break_buffer(self):
        return self.hp["entry_box_break_buffer_pct"] / 100

    def level_notional_schedule(self, *, balance: float, levels: int) -> list[float]:
        base = balance * (self.hp["base_level_notional_pct"] / 100)
        mult = float(self.hp["level_size_multiplier"])
        return [round(base * (mult ** index), 5) for index in range(levels)]

    @property
    def entry_box_failure_confirmed(self):
        entry_box_low = self._grid_state.get("entry_box_low")
        if entry_box_low is None:
            return False
        closes = [float(candle[2]) for candle in self.candles[-self.hp["entry_box_break_bars"] :]]
        if len(closes) < self.hp["entry_box_break_bars"]:
            return False
        return all(close < float(entry_box_low) for close in closes)

    @property
    def buffered_entry_box_failure_confirmed(self):
        entry_box_low = self._grid_state.get("entry_box_low")
        if entry_box_low is None:
            return False
        failure_level = float(entry_box_low) * (1 - float(self.entry_box_break_buffer))
        closes = [float(candle[2]) for candle in self.candles[-self.hp["entry_box_break_bars"] :]]
        if len(closes) < self.hp["entry_box_break_bars"]:
            return False
        return all(close < failure_level for close in closes)

    def activate_level_with_variant_sizing(self, *, state: dict, level_index: int, balance: float) -> dict:
        levels = list(state["levels"])
        filled_levels = set(state.get("filled_levels", set()))
        slices = list(state.get("slices", []))
        notionals = self.level_notional_schedule(balance=balance, levels=len(levels))
        notional = notionals[level_index]
        entry_price = float(levels[level_index])
        exit_price = float(levels[min(level_index + 1, len(levels) - 1)])
        qty = round(notional / entry_price, 8)
        slice_state = {
            "buy_level_index": level_index,
            "sell_level_index": min(level_index + 1, len(levels) - 1),
            "entry_price": entry_price,
            "exit_price": exit_price,
            "qty": qty,
            "notional": notional,
        }
        filled_levels.add(level_index)
        slices.append(slice_state)
        return {
            **state,
            "filled_levels": filled_levels,
            "slices": slices,
            "current_notional": state.get("current_notional", 0.0) + notional,
        }

    def build_runtime_decision_trace(self, *, current_position: dict | None) -> dict:
        state = getattr(self, "_grid_state", None) or self.build_grid_state()
        levels = [float(level) for level in state.get("levels", [])]
        slices = list(state.get("slices", []))
        notionals = self.level_notional_schedule(balance=float(self.balance), levels=len(levels)) if levels else []
        next_level_index = (
            next_buy_level_index(
                levels=levels,
                filled_levels=set(state.get("filled_levels", set())),
                current_price=float(self.price),
            )
            if levels
            else None
        )

        if next_level_index is not None:
            proposed_action = "open_long"
            should_emit = True
            reason_code = "entry_signal_emitted"
            reason_text = "price reached the next eligible grid level"
        elif slices:
            proposed_action = "none"
            should_emit = False
            reason_code = "waiting_take_profit"
            reason_text = "inventory exists and no new grid level is eligible"
        else:
            proposed_action = "none"
            should_emit = False
            reason_code = "no_entry_level_hit"
            reason_text = "price has not reached an eligible grid entry level"

        candle = list(self.current_candle)
        box_high = float(self.box_high)
        box_low = float(self.box_low)
        box_height = box_high - box_low
        selected_notional = notionals[next_level_index] if next_level_index is not None and notionals else None
        selected_level_price = levels[next_level_index] if next_level_index is not None and levels else None

        return {
            "market": {
                "candle_timestamp": int(candle[0]),
                "open": float(candle[1]),
                "close": float(candle[2]),
                "high": float(candle[3]),
                "low": float(candle[4]),
                "price": float(self.price),
            },
            "box": {
                "box_confirmed": bool(levels),
                "box_high": box_high,
                "box_low": box_low,
                "box_height": box_height,
                "box_width_pct": ((box_height / box_low) * 100) if box_low else None,
                "center_line": float(self.box_mid),
                "price_position_in_box": ((float(self.price) - box_low) / box_height) if box_height > 0 else None,
                "lower_bound": float(self.lower_bound),
                "entry_box_low": state.get("entry_box_low"),
                "entry_box_high": state.get("entry_box_high"),
                "entry_box_mid": state.get("entry_box_mid"),
            },
            "grid": {
                "grid_levels": len(levels),
                "grid_prices": levels,
                "hit_level_index": next_level_index,
                "eligible_new_level": next_level_index is not None,
                "occupied_level_indexes": sorted(set(state.get("filled_levels", set()))),
                "take_profit_targets": [float(slice_state["exit_price"]) for slice_state in slices],
            },
            "sizing": {
                "base_level_notional_pct": float(self.hp["base_level_notional_pct"]),
                "level_size_multiplier": float(self.hp["level_size_multiplier"]),
                "level_notionals": notionals,
                "selected_level_notional": selected_notional,
                "selected_level_fraction": (selected_notional / float(self.balance)) if selected_notional is not None else None,
            },
            "inventory": {
                "current_position_side": None if current_position is None else current_position.get("side"),
                "current_position_qty": None if current_position is None else current_position.get("qty"),
                "current_position_entry_price": None if current_position is None else current_position.get("entry_price"),
                "active_slices": slices,
                "slice_count": len(slices),
                "pending_inventory_release": False,
                "current_notional": float(state.get("current_notional", 0.0)),
            },
            "strategy_decision": {
                "intent": "long" if next_level_index is not None else "flat",
                "proposed_action": proposed_action,
                "should_emit_before_runtime_gates": should_emit,
                "reason_code": reason_code,
                "reason_text": reason_text,
                "signal_payload_preview": {
                    "source": "jesse",
                    "price": float(self.price),
                    "position_side": "long",
                    "qty": round(selected_notional / selected_level_price, 8)
                    if selected_notional is not None and selected_level_price not in (None, 0)
                    else None,
                },
            },
        }

    def go_long(self):
        self._grid_state = self.build_grid_state()
        self._grid_state["entry_box_low"] = float(self.box_low)
        self._grid_state["entry_box_high"] = float(self.box_high)
        self._grid_state["entry_box_mid"] = float(self.box_mid)
        level_index = next_buy_level_index(
            levels=self._grid_state["levels"],
            filled_levels=self._grid_state["filled_levels"],
            current_price=float(self.price),
        )
        if level_index is None:
            return
        next_state = self.activate_level_with_variant_sizing(
            state=self._grid_state,
            level_index=level_index,
            balance=float(self.balance),
        )
        self._grid_state = next_state
        qty = next_state["slices"][-1]["qty"]
        self.buy = qty, self.price

    def update_position(self):
        state = getattr(self, "_grid_state", None) or self.build_grid_state()
        self._grid_state = state
        if self.buffered_entry_box_failure_confirmed:
            self.liquidate()
            self._grid_state = self.build_grid_state()
            return
        if float(self.price) < float(self.lower_bound):
            self.liquidate()
            self._grid_state = self.build_grid_state()
            return

        slices = list(self._grid_state.get("slices", []))
        for slice_index, slice_state in enumerate(slices):
            opened_at_index = slice_state.get("opened_at_index")
            if opened_at_index is None:
                continue
            bars_held = self.index - int(opened_at_index)
            if should_release_stale_slice(
                bars_held=bars_held,
                required_bars=int(self.hp["inventory_release_bars"]),
                current_price=float(self.price),
                entry_price=float(slice_state["entry_price"]),
                buffer_pct=float(self.inventory_release_buffer),
            ):
                self.take_profit = (float(slice_state["qty"]), float(self.price))
                next_slices = [s for i, s in enumerate(slices) if i != slice_index]
                next_filled = set(self._grid_state.get("filled_levels", set()))
                next_filled.discard(slice_state["buy_level_index"])
                self._grid_state = {
                    **self._grid_state,
                    "slices": next_slices,
                    "filled_levels": next_filled,
                    "current_notional": float(self._grid_state.get("current_notional", 0.0)) - float(slice_state["notional"]),
                }
                return

        if not total_notional_cap_reached(
            current_notional=float(state.get("current_notional", 0.0)),
            balance=float(self.balance),
            max_total_notional_pct=float(self.hp["max_total_notional_pct"]),
        ):
            level_index = next_buy_level_index(
                levels=state["levels"],
                filled_levels=state["filled_levels"],
                current_price=float(self.price),
            )
            if level_index is not None:
                next_state = self.activate_level_with_variant_sizing(
                    state=state,
                    level_index=level_index,
                    balance=float(self.balance),
                )
                self._grid_state = next_state
                qty = next_state["slices"][-1]["qty"]
                self.buy = qty, self.price

        slices = self._grid_state.get("slices", [])
        if slices:
            self.take_profit = [(float(slice_state["qty"]), float(slice_state["exit_price"])) for slice_state in slices]
