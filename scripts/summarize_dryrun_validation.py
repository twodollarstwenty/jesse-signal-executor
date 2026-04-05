import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.shared.db import connect


def parse_positive_minutes(raw: str) -> int:
    value = int(raw)
    if value <= 0:
        raise argparse.ArgumentTypeError("--minutes must be a positive integer")
    return value


def build_window_start(*, now: datetime, minutes: int) -> datetime:
    return now - timedelta(minutes=minutes)


def fetch_summary(*, minutes: int) -> dict:
    now = datetime.now(timezone.utc)
    window_start = build_window_start(now=now, minutes=minutes)
    conn = connect()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*), MAX(signal_time)
                FROM signal_events
                WHERE signal_time >= %s
                """,
                (window_start,),
            )
            signal_count, latest_signal_time = cur.fetchone()

            cur.execute(
                """
                SELECT COUNT(*), MAX(created_at)
                FROM execution_events
                WHERE created_at >= %s
                """,
                (window_start,),
            )
            execution_count, latest_execution_time = cur.fetchone()

            cur.execute(
                """
                SELECT status, COUNT(*)
                FROM signal_events
                WHERE signal_time >= %s
                GROUP BY status
                """,
                (window_start,),
            )
            signal_status_counts = {status: count for status, count in cur.fetchall()}

        return {
            "window_minutes": minutes,
            "signal_count": signal_count,
            "execution_count": execution_count,
            "signal_status_counts": signal_status_counts,
            "latest_signal_time": latest_signal_time,
            "latest_execution_time": latest_execution_time,
        }
    finally:
        conn.close()


def render_summary(summary: dict) -> str:
    lines = [
        f"window_minutes: {summary['window_minutes']}",
        f"signal_count: {summary['signal_count']}",
        f"execution_count: {summary['execution_count']}",
    ]

    for key in ("execute", "ignored", "rejected"):
        lines.append(f"{key}: {summary['signal_status_counts'].get(key, 0)}")

    latest_signal_time = summary["latest_signal_time"]
    latest_execution_time = summary["latest_execution_time"]
    lines.append(f"latest_signal_time: {latest_signal_time.isoformat() if latest_signal_time else 'none'}")
    lines.append(f"latest_execution_time: {latest_execution_time.isoformat() if latest_execution_time else 'none'}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=parse_positive_minutes, default=60)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(render_summary(fetch_summary(minutes=args.minutes)))


if __name__ == "__main__":
    main()
