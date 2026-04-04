import os
import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    workspace = project_root / "runtime" / "jesse_workspace"

    os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
    os.environ.setdefault("POSTGRES_PORT", "5432")
    os.environ.setdefault("POSTGRES_DB", "jesse_db")
    os.environ.setdefault("POSTGRES_USER", "jesse_user")
    os.environ.setdefault("POSTGRES_PASSWORD", "password")

    os.chdir(workspace)

    sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(workspace / "strategies"))
    sys.path.insert(0, str(workspace))
    sys.path.insert(0, str(project_root / "strategies" / "jesse"))

    from apps.shared.db import connect
    from apps.executor_service.service import run_once
    from Ott2butKAMA import Ott2butKAMA

    conn = connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM execution_events")
                cur.execute("DELETE FROM signal_events")

        Ott2butKAMA.pos_size = property(lambda self: 1.0)
        Ott2butKAMA.current_candle = property(lambda self: [1712188800000, 2500.0, 2500.0, 2510.0, 2490.0, 100.0])
        Ott2butKAMA.price = property(lambda self: 2500.0)
        Ott2butKAMA.cross_down = property(lambda self: True)
        Ott2butKAMA.cross_up = property(lambda self: False)
        Ott2butKAMA.is_long = property(lambda self: True)
        Ott2butKAMA.is_short = property(lambda self: False)

        strategy = object.__new__(Ott2butKAMA)
        strategy.symbol = "ETH-USDT"
        strategy.timeframe = "5m"
        strategy.buy = None
        strategy.sell = None
        strategy.liquidate = lambda: None

        strategy.go_long()
        strategy.update_position()

        run_once()
        run_once()

        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT action, status FROM signal_events ORDER BY id")
                signal_rows = cur.fetchall()
                cur.execute("SELECT status, mode FROM execution_events ORDER BY id")
                execution_rows = cur.fetchall()

        print(f"signal_rows={signal_rows}")
        print(f"execution_rows={execution_rows}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
