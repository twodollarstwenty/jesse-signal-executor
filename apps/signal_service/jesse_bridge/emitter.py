from datetime import datetime, timezone

from apps.signal_service.writer import insert_signal


def candle_timestamp_to_iso(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def emit_signal(*, strategy: str, symbol: str, timeframe: str, candle_timestamp: int, action: str, payload: dict) -> None:
    insert_signal(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        signal_time=candle_timestamp_to_iso(candle_timestamp),
        action=action,
        payload=payload,
    )
