import os
import sys
from datetime import datetime, timezone, timedelta
from importlib import import_module
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# Map project DB env to the names Jesse expects before importing shared/Jesse-dependent modules.
if "PASSWORD" not in os.environ and "POSTGRES_PASSWORD" in os.environ:
    os.environ["PASSWORD"] = os.environ["POSTGRES_PASSWORD"]
if "HOST" not in os.environ and "POSTGRES_HOST" in os.environ:
    os.environ["HOST"] = os.environ["POSTGRES_HOST"]
if "PORT" not in os.environ and "POSTGRES_PORT" in os.environ:
    os.environ["PORT"] = os.environ["POSTGRES_PORT"]
if "DB_NAME" not in os.environ and "POSTGRES_DB" in os.environ:
    os.environ["DB_NAME"] = os.environ["POSTGRES_DB"]
if "USERNAME" not in os.environ and "POSTGRES_USER" in os.environ:
    os.environ["USERNAME"] = os.environ["POSTGRES_USER"]

from scripts.fetch_binance_kline_snapshot import fetch_recent_klines
from apps.shared.db import connect
from apps.runtime.instance_runtime import build_instance_paths
from scripts.summarize_dryrun_account import compute_current_equity, compute_realized_pnl, compute_unrealized_pnl
from scripts.build_current_position_panel import compute_position_qty
from strategies.shared.ott2butkama_core import evaluate_direction

STRATEGY_NAME = "Ott2butKAMA"
SYMBOL = "ETH-USDT"
TIMEFRAME = "5m"
ACTIVE_LOOP_STATE: dict | None = None
LAST_EMITTED_ACTION: str | None = None
LAST_PROCESSED_CANDLE_TS: int | None = None
LAST_EMITTED_ACTION_BY_CONTEXT: dict[Path, str] = {}
LAST_PROCESSED_CANDLE_TS_BY_CONTEXT: dict[Path, int] = {}
CST = timezone(timedelta(hours=8))


def normalize_symbol(symbol: str) -> str:
    if "-" in symbol:
        return symbol
    if symbol.endswith("USDT") and len(symbol) > 4:
        return f"{symbol[:-4]}-USDT"
    return symbol


def build_default_runtime_context() -> dict:
    return {
        "instance_id": "dryrun",
        "strategy_name": STRATEGY_NAME,
        "symbol": SYMBOL,
        "timeframe": TIMEFRAME,
        "capital_usdt": 1000.0,
        "sizing": {},
        "paths": {
            "last_action": Path(os.getenv("JESSE_LAST_ACTION_FILE", str(ROOT / "runtime" / "dryrun" / "last_action.txt"))),
            "last_candle": Path(os.getenv("JESSE_LAST_CANDLE_FILE", str(ROOT / "runtime" / "dryrun" / "last_candle_ts.txt"))),
        },
    }


def build_runtime_context(instance: dict, runtime_root: Path) -> dict:
    sizing = dict(instance["sizing"])
    return {
        "instance_id": instance["id"],
        "strategy_name": instance["strategy"],
        "symbol": normalize_symbol(instance["symbol"]),
        "timeframe": instance["timeframe"],
        "capital_usdt": instance["capital_usdt"],
        "sizing": sizing,
        "paths": build_instance_paths(runtime_root, instance["id"]),
    }


def get_last_action_file(context: dict | None = None) -> Path:
    runtime_context = context or build_default_runtime_context()
    return runtime_context["paths"]["last_action"]


def get_last_candle_file(context: dict | None = None) -> Path:
    runtime_context = context or build_default_runtime_context()
    return runtime_context["paths"]["last_candle"]


def read_last_processed_candle_ts(context: dict | None = None) -> int | None:
    path = get_last_candle_file(context)
    if not path.exists():
        return None
    text = path.read_text().strip()
    return int(text) if text else None


def write_last_processed_candle_ts(value: int, context: dict | None = None) -> None:
    path = get_last_candle_file(context)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(value))


def get_in_memory_last_processed_candle_ts(context: dict | None = None) -> int | None:
    if context is None:
        return LAST_PROCESSED_CANDLE_TS
    return LAST_PROCESSED_CANDLE_TS_BY_CONTEXT.get(get_last_candle_file(context))


def set_in_memory_last_processed_candle_ts(value: int, context: dict | None = None) -> None:
    global LAST_PROCESSED_CANDLE_TS

    if context is None:
        LAST_PROCESSED_CANDLE_TS = value
        return
    LAST_PROCESSED_CANDLE_TS_BY_CONTEXT[get_last_candle_file(context)] = value


def read_last_emitted_action(context: dict | None = None) -> str | None:
    path = get_last_action_file(context)
    if not path.exists():
        return None
    text = path.read_text().strip()
    return text or None


def write_last_emitted_action(action: str, context: dict | None = None) -> None:
    path = get_last_action_file(context)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(action)


def get_in_memory_last_emitted_action(context: dict | None = None) -> str | None:
    if context is None:
        return LAST_EMITTED_ACTION
    return LAST_EMITTED_ACTION_BY_CONTEXT.get(get_last_action_file(context))


def set_in_memory_last_emitted_action(action: str, context: dict | None = None) -> None:
    global LAST_EMITTED_ACTION

    if context is None:
        LAST_EMITTED_ACTION = action
        return
    LAST_EMITTED_ACTION_BY_CONTEXT[get_last_action_file(context)] = action


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


def render_flat_summary(*, timestamp: str, strategy: str, symbol: str, price: float, bias: str, action: str, emitted: bool, initial_capital: float = 1000.0, realized_pnl: float = 0.0, unrealized_pnl: float = 0.0, current_equity: float = 1000.0, latest_execution_result: str = "none") -> str:
    local_timestamp = datetime.fromisoformat(timestamp).astimezone(CST).isoformat()
    return (
        f"[{local_timestamp}] 策略={strategy} 交易对={symbol} 当前价={price} 初始资金={initial_capital:.2f} "
        f"已实现盈亏={realized_pnl:+.2f} 未实现盈亏={unrealized_pnl:+.2f} 当前权益={current_equity:.2f} "
        f"持仓=空仓 判断={bias} 动作={action} 已发送={'是' if emitted else '否'} 最近执行结果={latest_execution_result}"
    )


def render_position_summary(*, timestamp: str, strategy: str, symbol: str, current_price: float, position: dict, action: str, emitted: bool, initial_capital: float = 1000.0, realized_pnl: float = 0.0, unrealized_pnl: float = 0.0, current_equity: float = 1000.0, latest_execution_result: str = "none") -> str:
    pnl, pnl_pct = compute_position_pnl(position=position, current_price=current_price)
    local_timestamp = datetime.fromisoformat(timestamp).astimezone(CST).isoformat()
    side_label = "多" if position["side"] == "long" else "空"
    display_qty = compute_position_qty(
        initial_capital=initial_capital,
        leverage=10.0,
        position_fraction=0.2,
        current_price=current_price,
    )
    notional_usdt = round(display_qty * current_price, 2)
    return (
        f"[{local_timestamp}] 策略={strategy} 交易对={symbol} 持仓方向={side_label} 持仓数量(ETH)={display_qty} 持仓名义金额(USDT)={notional_usdt:.2f} "
        f"开仓价={position['entry_price']} 当前价={current_price} 已实现盈亏={realized_pnl:+.2f} 未实现盈亏={unrealized_pnl:+.2f} 当前权益={current_equity:.2f} "
        f"浮动盈亏={pnl:+.2f} 浮动收益率={pnl_pct:+.2f}% 动作={action} 已发送={'是' if emitted else '否'} 最近执行结果={latest_execution_result}"
    )


def fetch_persistent_position(*, symbol: str, instance_id: str | None = None) -> dict | None:
    def query_row(*, sql: str, params: tuple) -> tuple | None:
        conn = connect()
        try:
            with conn, conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone()
        finally:
            conn.close()

    row = None
    can_use_instance_filter = instance_id is not None
    if instance_id is not None:
        try:
            row = query_row(
                sql="""
                    SELECT side, qty, entry_price
                    FROM position_state
                    WHERE instance_id = %s AND symbol = %s
                    ORDER BY updated_at DESC, id DESC
                    LIMIT 1
                    """,
                params=(instance_id, symbol),
            )
        except Exception as exc:
            if 'instance_id' not in str(exc):
                raise
            can_use_instance_filter = False

    if not can_use_instance_filter:
        row = query_row(
            sql="""
                SELECT side, qty, entry_price
                FROM position_state
                WHERE symbol = %s
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                """,
            params=(symbol,),
        )

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


def build_loop_state_from_candles(snapshot: dict) -> dict:
    from strategies.shared.ott2butkama_features import build_feature_state

    close_prices = snapshot["close_prices"]
    price = close_prices[-1]

    if len(close_prices) < 3:
        intent = "flat"
        bias = "flat"
        position = None
    else:
        features = build_feature_state(
            closes=close_prices,
            ott_len=36,
            ott_percent=5.4,
            chop_rsi_len=17,
            chop_bandwidth=144,
        )
        intent = evaluate_direction(**features)
        bias = intent
        position = None if intent == "flat" else {"side": intent, "qty": 1.0, "entry_price": price}

    return {
        "timestamp": snapshot["timestamp"],
        "price": price,
        "candle_timestamp": snapshot["latest_timestamp"],
        "bias": bias,
        "position": position,
        "intent": intent,
        "action": "none",
        "last_action": "none",
    }


def normalize_intent_to_action(*, intent: str, position: dict | None) -> str:
    if position is None:
        return {"long": "open_long", "short": "open_short", "flat": "none"}.get(intent, "none")

    side = position["side"]
    if side == "long":
        return {"long": "none", "short": "close_long", "flat": "close_long"}.get(intent, "none")
    if side == "short":
        return {"short": "none", "long": "close_short", "flat": "close_short"}.get(intent, "none")
    return {"long": "open_long", "short": "open_short", "flat": "none"}.get(intent, "none")


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


def build_strategy_instance(context: dict | None = None):
    runtime_context = context or build_default_runtime_context()
    strategy_name = runtime_context["strategy_name"]
    strategy_module = import_module(strategy_name)
    strategy_class = getattr(strategy_module, strategy_name)

    return object.__new__(strategy_class)


def configure_strategy_for_signal_cycle(strategy, loop_state: dict | None = None, context: dict | None = None) -> None:
    runtime_context = context or build_default_runtime_context()
    loop_state = loop_state or getattr(strategy, "_loop_state", None) or build_default_loop_state()
    price = loop_state["price"]
    current_position = loop_state.get("current_position")
    side = current_position["side"] if current_position else None

    strategy.exchange = "Binance Perpetual Futures"
    strategy.instance_id = runtime_context["instance_id"]
    strategy.symbol = runtime_context["symbol"]
    strategy.timeframe = runtime_context["timeframe"]
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


def drive_strategy_cycle(strategy, loop_state: dict, context: dict | None = None) -> bool:
    from apps.signal_service.jesse_bridge.emitter import emit_signal

    runtime_context = context or build_default_runtime_context()
    loop_state = loop_state or getattr(strategy, "_loop_state", None) or build_default_loop_state()
    action = loop_state["action"]
    emitted = False

    if action == "open_long":
        strategy.go_long()
        emitted = True
    elif action == "open_short":
        strategy.go_short()
        emitted = True
    elif action == "close_long":
        emit_signal(
            instance_id=runtime_context["instance_id"],
            strategy=runtime_context["strategy_name"],
            symbol=runtime_context["symbol"].replace("-", ""),
            timeframe=runtime_context["timeframe"],
            candle_timestamp=int(loop_state["candle_timestamp"]),
            action="close_long",
            payload={"source": "jesse", "price": float(loop_state["price"]), "position_side": "long", "qty": 1.0},
        )
        emitted = True
    elif action == "close_short":
        emit_signal(
            instance_id=runtime_context["instance_id"],
            strategy=runtime_context["strategy_name"],
            symbol=runtime_context["symbol"].replace("-", ""),
            timeframe=runtime_context["timeframe"],
            candle_timestamp=int(loop_state["candle_timestamp"]),
            action="close_short",
            payload={"source": "jesse", "price": float(loop_state["price"]), "position_side": "short", "qty": 1.0},
        )
        emitted = True

    return emitted


def emit_strategy_signals(context: dict | None, loop_state: dict | None = None) -> dict:
    runtime_context = context or build_default_runtime_context()
    loop_state = loop_state or ACTIVE_LOOP_STATE or build_loop_state()
    if context is None:
        strategy = build_strategy_instance()
    else:
        strategy = build_strategy_instance(runtime_context)
    strategy._loop_state = loop_state
    if context is None:
        configure_strategy_for_signal_cycle(strategy)
    else:
        configure_strategy_for_signal_cycle(strategy, context=runtime_context)

    action = loop_state.get("action", "none")
    if context is None:
        remembered_action = read_last_emitted_action() or get_in_memory_last_emitted_action()
    else:
        remembered_action = read_last_emitted_action(runtime_context) or get_in_memory_last_emitted_action(runtime_context)
    persistent_position = fetch_persistent_position(
        symbol=runtime_context["symbol"].replace("-", ""),
        instance_id=runtime_context["instance_id"],
    )
    if action == "none":
        emitted = False
    elif action in {"close_long", "close_short"} and persistent_position is not None:
        if context is None:
            emitted = drive_strategy_cycle(strategy, loop_state)
        else:
            emitted = drive_strategy_cycle(strategy, loop_state, runtime_context)
        if emitted:
            set_in_memory_last_emitted_action(action, context)
            if context is None:
                write_last_emitted_action(action)
            else:
                write_last_emitted_action(action, runtime_context)
    elif action == remembered_action:
        emitted = False
    else:
        if context is None:
            emitted = drive_strategy_cycle(strategy, loop_state)
        else:
            emitted = drive_strategy_cycle(strategy, loop_state, runtime_context)
        if emitted:
            set_in_memory_last_emitted_action(action, context)
            if context is None:
                write_last_emitted_action(action)
            else:
                write_last_emitted_action(action, runtime_context)

    return {
        **loop_state,
        "emitted": emitted,
    }


def print_cycle_summary(loop_state: dict, context: dict | None = None) -> None:
    runtime_context = context or build_default_runtime_context()
    symbol = runtime_context["symbol"].replace("-", "")
    persistent_position = fetch_persistent_position(symbol=symbol, instance_id=runtime_context["instance_id"])
    initial_capital = float(runtime_context["capital_usdt"])
    realized_pnl = compute_realized_pnl(instance_id=runtime_context["instance_id"])
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
                strategy=runtime_context["strategy_name"],
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
            strategy=runtime_context["strategy_name"],
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


def run_cycle(context: dict | None = None) -> None:
    global ACTIVE_LOOP_STATE, LAST_PROCESSED_CANDLE_TS

    runtime_context = context or build_default_runtime_context()
    workspace = ensure_runtime_ready()
    prepare_import_path(workspace)
    current_time = datetime.now(timezone.utc)
    try:
        with workspace_cwd(workspace):
            snapshot = fetch_recent_klines(
                symbol=runtime_context["symbol"].replace("-", ""),
                interval=runtime_context["timeframe"],
            )
            snapshot["timestamp"] = current_time.isoformat()
            latest_candle_ts = int(snapshot["latest_timestamp"])
            remembered_candle_ts = read_last_processed_candle_ts(runtime_context)
            in_memory_candle_ts = get_in_memory_last_processed_candle_ts(context)
            if remembered_candle_ts is not None:
                set_in_memory_last_processed_candle_ts(remembered_candle_ts, context)
                in_memory_candle_ts = remembered_candle_ts
            if in_memory_candle_ts is None:
                set_in_memory_last_processed_candle_ts(latest_candle_ts, context)
                write_last_processed_candle_ts(latest_candle_ts, runtime_context)
                print(f"[{current_time.astimezone(CST).isoformat()}] 初始化 {runtime_context['timeframe']} 基线K线，不发单")
                return
            if in_memory_candle_ts == latest_candle_ts:
                print(f"[{current_time.astimezone(CST).isoformat()}] 等待新 {runtime_context['timeframe']} K 线")
                return
            loop_state = build_loop_state_from_candles(snapshot)
            persistent_position = fetch_persistent_position(symbol=runtime_context["symbol"].replace("-", ""))
            normalized_action = normalize_intent_to_action(intent=loop_state["intent"], position=persistent_position)
            loop_state["current_position"] = persistent_position
            loop_state["action"] = normalized_action
            loop_state["last_action"] = normalized_action
            ACTIVE_LOOP_STATE = loop_state
            if context is None:
                emitted_loop_state = emit_strategy_signals(None, loop_state)
            else:
                emitted_loop_state = emit_strategy_signals(runtime_context, loop_state)
            ACTIVE_LOOP_STATE = None
    except Exception as exc:
        print(f"[{current_time.astimezone(CST).isoformat()}] 行情获取失败，跳过本轮信号驱动: {exc.__class__.__name__}: {exc}")
        return
    set_in_memory_last_processed_candle_ts(latest_candle_ts, context)
    write_last_processed_candle_ts(latest_candle_ts, runtime_context)
    if isinstance(emitted_loop_state, dict):
        loop_state = emitted_loop_state
    else:
        loop_state = {**loop_state, "emitted": False}
    print_cycle_summary(loop_state, runtime_context)


def main() -> None:
    run_cycle()


if __name__ == "__main__":
    main()
