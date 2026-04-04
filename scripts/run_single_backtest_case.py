import argparse
import os
import sys
from datetime import date
from datetime import datetime, timezone
from pathlib import Path


def parse_iso_datetime(value: str, *, field_name: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed_dt = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed_date = date.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be ISO date or datetime") from exc
        return datetime.combine(parsed_date, datetime.min.time(), tzinfo=timezone.utc)

    if parsed_dt.tzinfo is None:
        return parsed_dt.replace(tzinfo=timezone.utc)
    return parsed_dt.astimezone(timezone.utc)


def to_milliseconds(value: str, *, field_name: str) -> int:
    return int(parse_iso_datetime(value, field_name=field_name).timestamp() * 1000)


def normalize_symbol(symbol: str) -> str:
    cleaned = symbol.strip().upper()
    if "-" in cleaned:
        return cleaned

    quote_assets = ("USDT", "USDC", "BUSD", "USD", "BTC", "ETH")
    for quote in quote_assets:
        if cleaned.endswith(quote) and len(cleaned) > len(quote):
            base = cleaned[: -len(quote)]
            return f"{base}-{quote}"
    return cleaned


def timeframe_to_minutes(timeframe: str) -> int:
    value = timeframe.strip().lower()
    unit = value[-1]
    amount = int(value[:-1])
    if unit == "m":
        return amount
    if unit == "h":
        return amount * 60
    if unit == "d":
        return amount * 24 * 60
    raise ValueError(f"unsupported timeframe: {timeframe}")


def ensure_python_paths() -> None:
    project_root = Path(__file__).resolve().parents[1]
    workspace = Path.cwd().resolve()
    workspace_strategies = workspace / "strategies"

    for entry in (project_root, workspace, workspace_strategies):
        entry_text = str(entry)
        if entry_text not in sys.path:
            sys.path.insert(0, entry_text)


def ensure_postgres_defaults() -> None:
    defaults = {
        "POSTGRES_DB": "jesse_db",
        "POSTGRES_USER": "jesse_user",
        "POSTGRES_NAME": "jesse_db",
        "POSTGRES_USERNAME": "jesse_user",
        "POSTGRES_PASSWORD": "password",
    }
    for key, value in defaults.items():
        os.environ.setdefault(key, value)


def fetch_candles_with_import_retry(
    *,
    exchange: str,
    symbol: str,
    start: str,
    start_ms: int,
    end_ms: int,
    warmup_candles_num: int,
):
    from jesse.research import get_candles
    from jesse.research import import_candles

    try:
        warmup_candles, candles = get_candles(
            exchange=exchange,
            symbol=symbol,
            timeframe="1m",
            start_date_timestamp=start_ms,
            finish_date_timestamp=end_ms,
            warmup_candles_num=warmup_candles_num,
            caching=False,
        )
        if candles is not None and len(candles) >= 2:
            return candles, warmup_candles
    except Exception:
        pass

    import_candles(exchange, symbol, start, show_progressbar=False)
    warmup_candles, candles = get_candles(
        exchange=exchange,
        symbol=symbol,
        timeframe="1m",
        start_date_timestamp=start_ms,
        finish_date_timestamp=end_ms,
        warmup_candles_num=warmup_candles_num,
        caching=False,
    )
    if candles is None or len(candles) < 2:
        raise RuntimeError("candles still missing after import")
    return candles, warmup_candles


def format_percent(value: object, *, scale: float = 1.0) -> str:
    if isinstance(value, str) and value.strip().endswith("%"):
        return value.strip()
    try:
        numeric = float(value) * scale
    except (TypeError, ValueError):
        numeric = 0.0
    return f"{numeric:.2f}%"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one Jesse research backtest case")
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--initial-balance", type=float, required=True)
    parser.add_argument("--fee", type=float, required=True)
    parser.add_argument("--leverage", type=int, required=True)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--exchange", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_python_paths()
    ensure_postgres_defaults()

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
    metrics = result.get("metrics", {})

    print(f"Total Closed Trades: {metrics.get('total', 0)}")
    print(f"Win Rate: {format_percent(metrics.get('win_rate', 0), scale=100.0)}")
    print(f"Net Profit: {format_percent(metrics.get('net_profit_percentage', 0))}")
    print(f"Max Drawdown: {format_percent(metrics.get('max_drawdown', 0))}")


if __name__ == "__main__":
    main()
