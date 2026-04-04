import json

from apps.executor_service.rules import decide_action
from apps.shared.db import connect


def build_execution_payload(*, signal_id: int, symbol: str, status: str) -> dict:
    return {
        "signal_id": signal_id,
        "symbol": symbol,
        "side": "unknown",
        "mode": "dry_run",
        "status": status,
        "detail_json": {"source": "executor_service"},
    }


def fetch_current_side(*, cur, symbol: str) -> str | None:
    cur.execute(
        """
        SELECT side
        FROM position_state
        WHERE symbol = %s
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """,
        (symbol,),
    )
    row = cur.fetchone()
    return None if row is None else row[0]


def run_once() -> None:
    conn = connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, symbol, action
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

                signal_id, symbol, action = row
                current_side = fetch_current_side(cur=cur, symbol=symbol)
                decision = decide_action(action, current_side)

                cur.execute(
                    "UPDATE signal_events SET status = %s, updated_at = NOW() WHERE id = %s AND status = 'new'",
                    (decision, signal_id),
                )
                if cur.rowcount != 1:
                    return

                payload = build_execution_payload(signal_id=signal_id, symbol=symbol, status=decision)
                cur.execute(
                    """
                    INSERT INTO execution_events (signal_id, symbol, side, mode, status, detail_json)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
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
