import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.notifications.wecom import send_text_message
from apps.shared.db import connect


def format_execution_event_message(row: dict) -> str:
    return "\n".join(
        [
            "[Dry-Run]",
            f"策略: {row['strategy']}",
            f"交易对: {row['symbol']}",
            f"动作: {row['action']}",
            f"处理结果: {row['decision']}",
            f"信号时间: {row.get('signal_time', 'N/A')}",
            f"执行时间: {row['created_at']}",
            f"价格: {row.get('price', 'N/A')}",
            f"仓位方向: {row.get('position_side', 'N/A')}",
            f"原因: {row['reason'] or 'N/A'}",
        ]
    )


def fetch_recent_execution_events(limit: int = 20) -> list[dict]:
    conn = connect()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT e.created_at, s.signal_time, s.strategy, e.symbol, s.action, e.status, NULL, s.payload_json
                FROM execution_events e
                JOIN signal_events s ON s.id = e.signal_id
                ORDER BY e.created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "created_at": row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0]),
            "signal_time": row[1].isoformat() if hasattr(row[1], "isoformat") else str(row[1]),
            "strategy": row[2],
            "symbol": row[3],
            "action": row[4],
            "decision": row[5],
            "reason": row[6],
            "price": (row[7] or {}).get("price", "N/A"),
            "position_side": (row[7] or {}).get("position_side", "N/A"),
        }
        for row in rows
    ]


def main() -> None:
    for row in reversed(fetch_recent_execution_events(limit=5)):
        send_text_message(format_execution_event_message(row))


if __name__ == "__main__":
    main()
