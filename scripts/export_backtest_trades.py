import argparse
import os
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def ensure_runtime_site_packages() -> None:
    venv_lib = ROOT / "runtime" / "jesse_workspace" / ".venv" / "lib"
    for python_dir in sorted(venv_lib.glob("python*")):
        site_packages = python_dir / "site-packages"
        if site_packages.exists() and str(site_packages) not in sys.path:
            sys.path.insert(0, str(site_packages))


@contextmanager
def workspace_cwd():
    previous_cwd = Path.cwd()
    workspace = ROOT / "runtime" / "jesse_workspace"
    try:
        os.chdir(workspace)
        yield workspace
    finally:
        os.chdir(previous_cwd)


from scripts.run_single_backtest_case import (
    ensure_python_paths,
    ensure_postgres_defaults,
    fetch_candles_with_import_retry,
    normalize_symbol,
    timeframe_to_minutes,
    to_milliseconds,
)


def format_timestamp_ms(value: float | int | None) -> str:
    if value is None:
        return ""
    return datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc).isoformat()


def format_holding_period(seconds: float | int | None) -> str:
    if seconds is None:
        return ""
    total_minutes = int(round(float(seconds) / 60))
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours}h {minutes}m"


def render_trades_table(trades: list[dict]) -> str:
    if not trades:
        return "No closed trades"

    columns = [
        "entry_time",
        "exit_time",
        "side",
        "entry_price",
        "exit_price",
        "qty",
        "pnl",
        "pnl_pct",
        "holding_period",
    ]
    widths = {column: len(column) for column in columns}
    for trade in trades:
        for column in columns:
            widths[column] = max(widths[column], len(str(trade.get(column, ""))))

    header = " | ".join(column.ljust(widths[column]) for column in columns)
    divider = "-+-".join("-" * widths[column] for column in columns)
    rows = [
        " | ".join(str(trade.get(column, "")).ljust(widths[column]) for column in columns)
        for trade in trades
    ]
    return "\n".join([header, divider, *rows])


def extract_trades(result: dict) -> list[dict]:
    raw_trades = result.get("trades", []) or []
    return [
        {
            "entry_time": format_timestamp_ms(trade.get("opened_at")),
            "exit_time": format_timestamp_ms(trade.get("closed_at")),
            "side": trade.get("type", ""),
            "entry_price": trade.get("entry_price", ""),
            "exit_price": trade.get("exit_price", ""),
            "qty": trade.get("qty", ""),
            "pnl": trade.get("PNL", ""),
            "pnl_pct": trade.get("PNL_percentage", ""),
            "holding_period": format_holding_period(trade.get("holding_period")),
        }
        for trade in raw_trades
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export backtest trade details")
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--initial-balance", type=float, default=10000)
    parser.add_argument("--fee", type=float, default=0.0004)
    parser.add_argument("--leverage", type=int, default=10)
    parser.add_argument("--mode", default="futures")
    parser.add_argument("--exchange", default="Binance Perpetual Futures")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with workspace_cwd():
        ensure_python_paths()
        ensure_postgres_defaults()
        ensure_runtime_site_packages()

        from jesse.research import backtest

        symbol = normalize_symbol(args.symbol)
        start_ms = to_milliseconds(args.start, field_name="start")
        end_ms = to_milliseconds(args.end, field_name="end")
        warmup_trading_candles = 210
        warmup_candles_num = warmup_trading_candles * timeframe_to_minutes(args.timeframe)

        candles, warmup_candles = fetch_candles_with_import_retry(
            exchange=args.exchange,
            symbol=symbol,
            start=args.start,
            start_ms=start_ms,
            end_ms=end_ms,
            warmup_candles_num=warmup_candles_num,
        )

        routes = [
            {
                "exchange": args.exchange,
                "strategy": args.strategy,
                "symbol": symbol,
                "timeframe": args.timeframe,
            }
        ]
        candle_key = f"{args.exchange}-{symbol}"
        candles_payload = {
            candle_key: {
                "exchange": args.exchange,
                "symbol": symbol,
                "candles": candles,
            }
        }
        warmup_payload = None
        if warmup_candles is not None and len(warmup_candles) >= 2:
            warmup_payload = {
                candle_key: {
                    "exchange": args.exchange,
                    "symbol": symbol,
                    "candles": warmup_candles,
                }
            }

        config = {
            "starting_balance": args.initial_balance,
            "fee": args.fee,
            "type": args.mode,
            "futures_leverage": args.leverage,
            "futures_leverage_mode": "cross",
            "exchange": args.exchange,
            "warm_up_candles": warmup_trading_candles,
        }
        result = backtest(
            config=config,
            routes=routes,
            data_routes=[],
            candles=candles_payload,
            warmup_candles=warmup_payload,
        )
        print(render_trades_table(extract_trades(result)))


if __name__ == "__main__":
    main()
