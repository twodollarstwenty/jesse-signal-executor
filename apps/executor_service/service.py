import json

from apps.executor_service.state_machine import decide_transition, normalize_side
from apps.shared.db import connect


def build_execution_payload(*, instance_id: str, signal_id: int, symbol: str, status: str) -> dict:
    return {
        "instance_id": instance_id,
        "signal_id": signal_id,
        "symbol": symbol,
        "side": "unknown",
        "mode": "dry_run",
        "status": status,
        "detail_json": {"source": "executor_service"},
    }


def build_position_payload(*, instance_id: str, symbol: str, side: str, signal_payload: dict) -> dict:
    if side == "flat":
        return {
            "instance_id": instance_id,
            "symbol": symbol,
            "side": "flat",
            "qty": 0.0,
            "entry_price": 0.0,
            "state_json": {},
        }

    return {
        "instance_id": instance_id,
        "symbol": symbol,
        "side": side,
        "qty": float(signal_payload.get("qty", 1.0)),
        "entry_price": float(signal_payload.get("price", 0.0)),
        "state_json": {},
    }


def fetch_current_side(*, cur, instance_id: str) -> str | None:
    cur.execute(
        """
        SELECT side
        FROM position_state
        WHERE instance_id = %s
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """,
        (instance_id,),
    )
    row = cur.fetchone()
    return None if row is None else row[0]


def upsert_position_side(*, cur, position_payload: dict) -> None:
    cur.execute(
        """
        INSERT INTO position_state (instance_id, symbol, side, qty, entry_price, state_json)
        VALUES (%s, %s, %s, %s, %s, %s::jsonb)
        """,
        (
            position_payload["instance_id"],
            position_payload["symbol"],
            position_payload["side"],
            position_payload["qty"],
            position_payload["entry_price"],
            json.dumps(position_payload["state_json"]),
        ),
    )


def run_once() -> None:
    conn = connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, instance_id, symbol, action, payload_json
                    FROM signal_events
                    WHERE status = 'new'
                    ORDER BY id ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                    """
                )
                row = cur.fetchone()
                if row is None:
                    return

                signal_id, instance_id, symbol, action, signal_payload = row

                cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s)::bigint)", (instance_id,))

                current_side = fetch_current_side(cur=cur, instance_id=instance_id)
                normalized_current_side = normalize_side(current_side)
                decision, next_state = decide_transition(current_side=current_side, signal_action=action)

                if decision == "execute" and next_state != normalized_current_side:
                    position_payload = build_position_payload(
                        instance_id=instance_id,
                        symbol=symbol,
                        side=next_state,
                        signal_payload=signal_payload or {},
                    )
                    upsert_position_side(cur=cur, position_payload=position_payload)

                cur.execute(
                    "UPDATE signal_events SET status = %s, updated_at = NOW() WHERE id = %s AND status = 'new'",
                    (decision, signal_id),
                )
                if cur.rowcount != 1:
                    return

                payload = build_execution_payload(
                    instance_id=instance_id,
                    signal_id=signal_id,
                    symbol=symbol,
                    status=decision,
                )
                cur.execute(
                    """
                    INSERT INTO execution_events (instance_id, signal_id, symbol, side, mode, status, detail_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        payload["instance_id"],
                        payload["signal_id"],
                        payload["symbol"],
                        payload["side"],
                        payload["mode"],
                        payload["status"],
                        json.dumps(payload["detail_json"]),
                    ),
                )
    finally:
        conn.close()
