import hashlib
import json
import math

from apps.shared.db import connect


def build_signal_hash(*, instance_id: str, strategy: str, symbol: str, timeframe: str, signal_time: str, action: str) -> str:
    payload = f"{instance_id}|{strategy}|{symbol}|{timeframe}|{signal_time}|{action}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_decision_hash(
    *, instance_id: str, strategy: str, symbol: str, timeframe: str, candle_timestamp: int
) -> str:
    payload = f"{instance_id}|{strategy}|{symbol}|{timeframe}|{candle_timestamp}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_json_value(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if not isinstance(value, (str, bytes, bool, int, float, dict, list, tuple)) and hasattr(value, "__float__"):
        try:
            float_value = float(value)
        except (TypeError, ValueError):
            pass
        else:
            if not math.isfinite(float_value):
                return None
            return float_value
    if isinstance(value, dict):
        return {key: _normalize_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize_json_value(item) for item in value]
    return value


def insert_signal(
    *, instance_id: str, strategy: str, symbol: str, timeframe: str, signal_time: str, action: str, payload: dict
) -> None:
    signal_hash = build_signal_hash(
        instance_id=instance_id,
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
                    INSERT INTO signal_events (instance_id, strategy, symbol, timeframe, signal_time, action, signal_hash, status, payload_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (signal_hash) DO NOTHING
                    """,
                    (instance_id, strategy, symbol, timeframe, signal_time, action, signal_hash, "new", json.dumps(payload)),
                )
    finally:
        conn.close()


def insert_signal_decision(
    *,
    instance_id: str,
    strategy: str,
    symbol: str,
    timeframe: str,
    signal_time: str,
    candle_timestamp: int,
    intent: str,
    action: str,
    emitted: bool,
    decision_status: str,
    reason_code: str,
    payload: dict,
) -> None:
    decision_hash = build_decision_hash(
        instance_id=instance_id,
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        candle_timestamp=candle_timestamp,
    )
    normalized_payload = _normalize_json_value(payload)
    conn = connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO signal_decision_events (
                        instance_id,
                        strategy,
                        symbol,
                        timeframe,
                        signal_time,
                        candle_timestamp,
                        decision_hash,
                        intent,
                        action,
                        emitted,
                        decision_status,
                        reason_code,
                        payload_json
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (decision_hash) DO NOTHING
                    """,
                    (
                        instance_id,
                        strategy,
                        symbol,
                        timeframe,
                        signal_time,
                        candle_timestamp,
                        decision_hash,
                        intent,
                        action,
                        emitted,
                        decision_status,
                        reason_code,
                        json.dumps(normalized_payload),
                    ),
                )
    finally:
        conn.close()
