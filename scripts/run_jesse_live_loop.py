import os
import sys
from datetime import datetime, timezone
from importlib import import_module
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STRATEGY_NAME = "Ott2butKAMA"
SYMBOL = "ETH-USDT"
TIMEFRAME = "5m"
ACTIVE_LOOP_STATE: dict | None = None


def compute_position_pnl(*, position: dict, current_price: float) -> tuple[float, float]:
    side = position["side"]
    qty = float(position["qty"])
    entry_price = float(position["entry_price"])

    if side == "short":
        pnl = (entry_price - current_price) * qty
        pnl_pct = ((entry_price - current_price) / entry_price) * 100
    else:
        pnl = (current_price - entry_price) * qty
        pnl_pct = ((current_price - entry_price) / entry_price) * 100

    return round(pnl, 2), round(pnl_pct, 2)


def render_flat_summary(*, timestamp: str, strategy: str, symbol: str, price: float, bias: str, action: str, emitted: bool) -> str:
    return f"[{timestamp}] strategy={strategy} symbol={symbol} price={price} position=flat bias={bias} action={action} emitted={'yes' if emitted else 'no'}"


def render_position_summary(*, timestamp: str, strategy: str, symbol: str, current_price: float, position: dict, action: str, emitted: bool) -> str:
    pnl, pnl_pct = compute_position_pnl(position=position, current_price=current_price)
    return (
        f"[{timestamp}] strategy={strategy} symbol={symbol} side={position['side']} qty={position['qty']} "
        f"entry={position['entry_price']} price={current_price} pnl={pnl:+.2f} pnl_pct={pnl_pct:+.2f}% "
        f"action={action} emitted={'yes' if emitted else 'no'}"
    )


def build_loop_state(now: datetime | None = None) -> dict:
    current_time = now or datetime.now(timezone.utc)
    step = int(current_time.timestamp() // 10)
    phase = step % 8
    price_offset = (phase - 3) * 7.5
    drift = (step % 3) * 1.2
    current_price = round(2500.0 + price_offset + drift, 2)
    candle_timestamp = int(current_time.timestamp() * 1000)

    position = None
    bias = "flat"
    action = "none"

    if phase in {1, 2, 3}:
        position = {
            "side": "long",
            "qty": 1.0,
            "entry_price": round(current_price - (10.0 + phase), 2),
        }
        bias = "long"
        action = "open_long" if phase == 1 else ("close_long" if phase == 3 else "none")
    elif phase in {5, 6, 7}:
        position = {
            "side": "short",
            "qty": 1.0,
            "entry_price": round(current_price + (10.0 + (phase - 4)), 2),
        }
        bias = "short"
        action = "open_short" if phase == 5 else ("close_short" if phase == 7 else "none")

    return {
        "timestamp": current_time.isoformat(),
        "step": step,
        "phase": phase,
        "price": current_price,
        "candle_timestamp": candle_timestamp,
        "bias": bias,
        "position": position,
        "action": action,
        "last_action": action,
    }


def build_default_loop_state() -> dict:
    return {
        "timestamp": "2024-04-04T00:00:00+00:00",
        "step": 0,
        "phase": 0,
        "price": 2500.0,
        "candle_timestamp": 1712188800000,
        "bias": "long",
        "position": {"side": "long", "qty": 1.0, "entry_price": 2500.0},
        "action": "close_long",
        "last_action": "close_long",
    }


def build_workspace_path() -> Path:
    return ROOT / "runtime" / "jesse_workspace"


def ensure_runtime_ready() -> Path:
    workspace = build_workspace_path()
    if not workspace.exists():
        raise FileNotFoundError("runtime/jesse_workspace is missing; run bootstrap first")
    if not (workspace / ".venv").exists():
        raise FileNotFoundError("runtime/jesse_workspace/.venv is missing; run bootstrap first")
    return workspace


def prepare_import_path(workspace: Path) -> None:
    desired_paths = [
        str(workspace),
        str(workspace / "strategies"),
        str(ROOT),
        str(ROOT / "strategies" / "jesse"),
    ]
    existing_paths = [path for path in sys.path if path not in desired_paths]
    sys.path[:] = desired_paths + existing_paths


@contextmanager
def workspace_cwd(workspace: Path):
    previous_cwd = Path.cwd()
    try:
        os.chdir(workspace)
        yield
    finally:
        os.chdir(previous_cwd)


def _set_runtime_attr(strategy, name: str, value) -> None:
    descriptor = getattr(type(strategy), name, None)
    if isinstance(descriptor, property) and descriptor.fset is None:
        runtime_overrides = getattr(strategy, "_runtime_overrides", {})
        runtime_overrides[name] = value
        strategy._runtime_overrides = runtime_overrides
        def getter(self, attr=name, original=descriptor):
            overrides = getattr(self, "_runtime_overrides", {})
            if attr in overrides:
                return overrides[attr]
            return original.fget(self)

        setattr(type(strategy), name, property(getter))
        return

    setattr(strategy, name, value)


def build_strategy_instance():
    Ott2butKAMA = import_module(STRATEGY_NAME).Ott2butKAMA

    return object.__new__(Ott2butKAMA)


def configure_strategy_for_signal_cycle(strategy, loop_state: dict | None = None) -> None:
    loop_state = loop_state or getattr(strategy, "_loop_state", None) or build_default_loop_state()
    price = loop_state["price"]
    side = loop_state["position"]["side"] if loop_state["position"] else None

    strategy.exchange = "Binance Perpetual Futures"
    strategy.symbol = SYMBOL
    strategy.timeframe = TIMEFRAME
    strategy.buy = None
    strategy.sell = None
    strategy.liquidate = lambda: None
    _set_runtime_attr(strategy, "pos_size", 1.0)
    _set_runtime_attr(strategy, "current_candle", [loop_state["candle_timestamp"], price, price, price + 10.0, price - 10.0, 100.0])
    _set_runtime_attr(strategy, "price", price)
    _set_runtime_attr(strategy, "cross_down", loop_state["action"] == "close_long")
    _set_runtime_attr(strategy, "cross_up", loop_state["action"] == "close_short")
    _set_runtime_attr(strategy, "is_long", side == "long")
    _set_runtime_attr(strategy, "is_short", side == "short")


def drive_strategy_cycle(strategy, loop_state: dict) -> bool:
    loop_state = loop_state or getattr(strategy, "_loop_state", None) or build_default_loop_state()
    action = loop_state["action"]
    emitted = False

    if action == "open_long":
        strategy.go_long()
        emitted = True
    elif action == "open_short":
        strategy.go_short()
        emitted = True
    elif action in {"close_long", "close_short"}:
        strategy.update_position()
        emitted = True

    return emitted


def emit_strategy_signals(loop_state: dict | None = None) -> dict:
    loop_state = loop_state or ACTIVE_LOOP_STATE or build_loop_state()
    strategy = build_strategy_instance()
    strategy._loop_state = loop_state
    configure_strategy_for_signal_cycle(strategy)
    emitted = drive_strategy_cycle(strategy, loop_state)

    return {
        **loop_state,
        "emitted": emitted,
    }


def print_cycle_summary(loop_state: dict) -> None:
    symbol = SYMBOL.replace("-", "")

    if loop_state["position"] is None:
        print(
            render_flat_summary(
                timestamp=loop_state["timestamp"],
                strategy=STRATEGY_NAME,
                symbol=symbol,
                price=loop_state["price"],
                bias=loop_state["bias"],
                action=loop_state["action"],
                emitted=loop_state["emitted"],
            )
        )
        return

    print(
        render_position_summary(
            timestamp=loop_state["timestamp"],
            strategy=STRATEGY_NAME,
            symbol=symbol,
            current_price=loop_state["price"],
            position=loop_state["position"],
            action=loop_state["action"],
            emitted=loop_state["emitted"],
        )
    )


def run_cycle() -> None:
    global ACTIVE_LOOP_STATE

    workspace = ensure_runtime_ready()
    prepare_import_path(workspace)
    loop_state = build_loop_state()
    ACTIVE_LOOP_STATE = loop_state
    with workspace_cwd(workspace):
        emitted_loop_state = emit_strategy_signals()
    ACTIVE_LOOP_STATE = None
    if isinstance(emitted_loop_state, dict):
        loop_state = emitted_loop_state
    else:
        loop_state = {**loop_state, "emitted": False}
    print_cycle_summary(loop_state)


def main() -> None:
    run_cycle()


if __name__ == "__main__":
    main()
