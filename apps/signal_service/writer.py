import hashlib
import json

from apps.shared.db import connect


def build_signal_hash(*, strategy: str, symbol: str, timeframe: str, signal_time: str, action: str) -> str:
    payload = f"{strategy}|{symbol}|{timeframe}|{signal_time}|{action}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def insert_signal(*, strategy: str, symbol: str, timeframe: str, signal_time: str, action: str, payload: dict) -> None:
    signal_hash = build_signal_hash(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        signal_time=signal_time,
        action=action,
    )
    conn = connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO signal_events (strategy, symbol, timeframe, signal_time, action, signal_hash, status, payload_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (signal_hash) DO NOTHING
                    """,
                    (strategy, symbol, timeframe, signal_time, action, signal_hash, "new", json.dumps(payload)),
                )
    finally:
        conn.close()
