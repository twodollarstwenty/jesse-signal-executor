import os
import sys
from datetime import datetime, timezone, timedelta
from importlib import import_module
from contextlib import contextmanager
from pathlib import Path

from scripts.fetch_binance_market_snapshot import fetch_ticker_price
from apps.shared.db import connect
from scripts.summarize_dryrun_account import compute_current_equity, compute_realized_pnl, compute_unrealized_pnl

ROOT = Path(__file__).resolve().parents[1]
STRATEGY_NAME = "Ott2butKAMA"
SYMBOL = "ETH-USDT"
TIMEFRAME = "5m"
ACTIVE_LOOP_STATE: dict | None = None
LAST_EMITTED_ACTION: str | None = None
CST = timezone(timedelta(hours=8))


def get_last_action_file() -> Path:
    return Path(os.getenv("JESSE_LAST_ACTION_FILE", str(ROOT / "runtime" / "dryrun" / "last_action.txt")))


def read_last_emitted_action() -> str | None:
    path = get_last_action_file()
    if not path.exists():
        return None
    text = path.read_text().strip()
    return text or None


def write_last_emitted_action(action: str) -> None:
    path = get_last_action_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(action)


def compute_position_pnl(*, position: dict, current_price: float) -> tuple[float, float]:
    side = position["side"]
    qty = float(position["qty"])
    entry_price = float(position["entry_price"])

    if entry_price <= 0:
        return 0.0, 0.0

    if side == "short":
        pnl = (entry_price - current_price) * qty
        pnl_pct = ((entry_price - current_price) / entry_price) * 100
    else:
        pnl = (current_price - entry_price) * qty
        pnl_pct = ((current_price - entry_price) / entry_price) * 100

    return round(pnl, 2), round(pnl_pct, 2)


def render_flat_summary(*, timestamp: str, strategy: str, symbol: str, price: float, bias: str, action: str, emitted: bool, initial_capital: float = 1000.0, realized_pnl: float = 0.0, unrealized_pnl: float = 0.0, current_equity: float = 1000.0) -> str:
    local_timestamp = datetime.fromisoformat(timestamp).astimezone(CST).isoformat()
    return (
        f"[{local_timestamp}] 策略={strategy} 交易对={symbol} 当前价={price} 初始资金={initial_capital:.2f} "
        f"已实现盈亏={realized_pnl:+.2f} 未实现盈亏={unrealized_pnl:+.2f} 当前权益={current_equity:.2f} "
        f"持仓=空仓 判断={bias} 动作={action} 已发送={'是' if emitted else '否'}"
    )


def render_position_summary(*, timestamp: str, strategy: str, symbol: str, current_price: float, position: dict, action: str, emitted: bool, initial_capital: float = 1000.0, realized_pnl: float = 0.0, unrealized_pnl: float = 0.0, current_equity: float = 1000.0) -> str:
    pnl, pnl_pct = compute_position_pnl(position=position, current_price=current_price)
    local_timestamp = datetime.fromisoformat(timestamp).astimezone(CST).isoformat()
    side_label = "多" if position["side"] == "long" else "空"
    notional_usdt = round(float(position["qty"]) * current_price, 2)
    return (
        f"[{local_timestamp}] 策略={strategy} 交易对={symbol} 持仓方向={side_label} 持仓数量(ETH)={position['qty']} 持仓名义金额(USDT)={notional_usdt:.2f} "
        f"开仓价={position['entry_price']} 当前价={current_price} 已实现盈亏={realized_pnl:+.2f} 未实现盈亏={unrealized_pnl:+.2f} 当前权益={current_equity:.2f} "
        f"浮动盈亏={pnl:+.2f} 浮动收益率={pnl_pct:+.2f}% 动作={action} 已发送={'是' if emitted else '否'}"
    )


def fetch_persistent_position(*, symbol: str) -> dict | None:
    conn = connect()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT side, qty, entry_price
                FROM position_state
                WHERE symbol = %s
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                """,
                (symbol,),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    side, qty, entry_price = row
    if side == "flat":
        return None
    return {"side": side, "qty": float(qty), "entry_price": float(entry_price)}


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


def build_loop_state_from_market_snapshot(snapshot: dict) -> dict:
    price = float(snapshot["price"])
    action = "none"
    bias = "flat"
    position = None

    cents = int(price * 10) % 4
    if cents == 0:
        action = "open_long"
        bias = "long"
        position = {"side": "long", "qty": 1.0, "entry_price": round(price - 10, 2)}
    elif cents == 1:
        action = "close_long"
        bias = "long"
        position = {"side": "long", "qty": 1.0, "entry_price": round(price - 12, 2)}
    elif cents == 2:
        action = "open_short"
        bias = "short"
        position = {"side": "short", "qty": 1.0, "entry_price": round(price + 10, 2)}
    elif cents == 3:
        action = "close_short"
        bias = "short"
        position = {"side": "short", "qty": 1.0, "entry_price": round(price + 12, 2)}

    return {
        "timestamp": snapshot["timestamp"],
        "price": price,
        "candle_timestamp": int(snapshot.get("candle_timestamp", 0)),
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
    global LAST_EMITTED_ACTION

    loop_state = loop_state or ACTIVE_LOOP_STATE or build_loop_state()
    strategy = build_strategy_instance()
    strategy._loop_state = loop_state
    configure_strategy_for_signal_cycle(strategy)

    action = loop_state.get("action", "none")
    remembered_action = read_last_emitted_action() or LAST_EMITTED_ACTION
    if action == "none":
        emitted = False
    elif action == remembered_action:
        emitted = False
    else:
        emitted = drive_strategy_cycle(strategy, loop_state)
        if emitted:
            LAST_EMITTED_ACTION = action
            write_last_emitted_action(action)

    return {
        **loop_state,
        "emitted": emitted,
    }


def print_cycle_summary(loop_state: dict) -> None:
    symbol = SYMBOL.replace("-", "")
    persistent_position = fetch_persistent_position(symbol=symbol)
    initial_capital = 1000.0
    realized_pnl = compute_realized_pnl()
    unrealized_pnl = compute_unrealized_pnl(position=persistent_position, current_price=loop_state["price"])
    current_equity = compute_current_equity(
        initial_capital=initial_capital,
        realized_pnl=realized_pnl,
        unrealized_pnl=unrealized_pnl,
    )

    if persistent_position is None:
        print(
            render_flat_summary(
                timestamp=loop_state["timestamp"],
                strategy=STRATEGY_NAME,
                symbol=symbol,
                price=loop_state["price"],
                bias=loop_state["bias"],
                action=loop_state["action"],
                emitted=loop_state["emitted"],
                initial_capital=initial_capital,
                realized_pnl=realized_pnl,
                unrealized_pnl=unrealized_pnl,
                current_equity=current_equity,
            )
        )
        return

    print(
        render_position_summary(
            timestamp=loop_state["timestamp"],
            strategy=STRATEGY_NAME,
            symbol=symbol,
            current_price=loop_state["price"],
            position=persistent_position,
            action=loop_state["action"],
            emitted=loop_state["emitted"],
            initial_capital=initial_capital,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            current_equity=current_equity,
        )
    )


def run_cycle() -> None:
    global ACTIVE_LOOP_STATE

    workspace = ensure_runtime_ready()
    prepare_import_path(workspace)
    current_time = datetime.now(timezone.utc)
    try:
        snapshot = fetch_ticker_price(symbol=SYMBOL.replace("-", ""))
        snapshot["timestamp"] = current_time.isoformat()
        snapshot["candle_timestamp"] = int(current_time.timestamp() * 1000)
        loop_state = build_loop_state_from_market_snapshot(snapshot)
    except Exception:
        loop_state = {
            "timestamp": current_time.isoformat(),
            "price": 0.0,
            "candle_timestamp": int(current_time.timestamp() * 1000),
            "bias": "flat",
            "position": None,
            "action": "none",
            "last_action": "none",
            "emitted": False,
        }
        print(f"[{datetime.fromisoformat(loop_state['timestamp']).astimezone(CST).isoformat()}] 行情获取失败，跳过本轮信号驱动")
        print_cycle_summary(loop_state)
        return
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
