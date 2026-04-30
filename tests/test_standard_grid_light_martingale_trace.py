from strategies.jesse.StandardGrid_LightMartingale_v1 import StandardGrid_LightMartingale_v1
from scripts.run_jesse_live_loop import _set_runtime_attr


def make_strategy():
    strategy = object.__new__(StandardGrid_LightMartingale_v1)
    strategy.hp = {
        "base_level_notional_pct": 4.25,
        "level_size_multiplier": 1.10,
        "grid_levels": 4,
        "center_ma_len": 3,
        "upper_band_pct": 10,
        "lower_band_pct": 10,
        "box_lookback": 4,
        "breakout_lookback": 3,
        "min_box_width_pct": 3,
        "max_box_width_pct": 15,
        "inventory_release_bars": 96,
        "inventory_release_buffer_pct": 5,
        "entry_box_break_bars": 3,
        "entry_box_break_buffer_pct": 2,
        "max_total_notional_pct": 50,
    }
    strategy._grid_state = {
        "levels": [2200.0, 2250.0, 2300.0, 2350.0],
        "filled_levels": {0},
        "slices": [
            {
                "buy_level_index": 0,
                "sell_level_index": 1,
                "entry_price": 2200.0,
                "exit_price": 2250.0,
                "qty": 0.02,
                "notional": 44.0,
                "opened_at_index": 100,
            }
        ],
        "current_notional": 44.0,
        "entry_box_low": 2180.0,
        "entry_box_high": 2380.0,
        "entry_box_mid": 2280.0,
    }
    strategy.balance = 1000.0
    candles = [
        [1714480800000, 2265.0, 2255.0, 2275.0, 2245.0, 100.0],
        [1714481100000, 2260.0, 2250.0, 2270.0, 2240.0, 100.0],
        [1714481400000, 2255.0, 2245.0, 2265.0, 2235.0, 100.0],
        [1714481700000, 2260.0, 2240.0, 2270.0, 2230.0, 100.0],
    ]
    _set_runtime_attr(strategy, "price", 2240.0)
    _set_runtime_attr(strategy, "current_candle", candles[-1])
    strategy.index = 120
    _set_runtime_attr(strategy, "candles", candles)
    return strategy


def test_build_runtime_decision_trace_contains_required_sections():
    strategy = make_strategy()

    trace = strategy.build_runtime_decision_trace(current_position=None)

    assert set(trace) == {"market", "box", "grid", "sizing", "inventory", "strategy_decision"}
    assert trace["market"]["price"] == 2240.0
    assert "box_confirmed" in trace["box"]
    assert "grid_prices" in trace["grid"]
    assert "level_notionals" in trace["sizing"]
    assert "active_slices" in trace["inventory"]
    assert "reason_code" in trace["strategy_decision"]


def test_build_runtime_decision_trace_reports_waiting_take_profit_when_inventory_exists_and_no_new_level():
    strategy = make_strategy()
    _set_runtime_attr(strategy, "price", 2400.0)
    _set_runtime_attr(strategy, "current_candle", [1714481700000, 2405.0, 2400.0, 2410.0, 2390.0, 100.0])

    trace = strategy.build_runtime_decision_trace(current_position={"side": "long", "qty": 0.02, "entry_price": 2200.0})

    assert trace["strategy_decision"]["proposed_action"] == "none"
    assert trace["strategy_decision"]["reason_code"] == "waiting_take_profit"
