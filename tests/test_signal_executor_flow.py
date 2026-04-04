import os
from datetime import datetime, timezone

import pytest

from apps.shared.db import connect
from apps.signal_service.writer import insert_signal
from apps.executor_service.service import run_once
from tests.db_testkit import apply_test_db_env, clear_event_tables, init_db_schema


def test_signal_executor_flow_execute_path(monkeypatch):
    if os.getenv("PYTEST_XDIST_WORKER"):
        pytest.skip("uses clear_event_tables on shared tables; run without xdist workers")

    apply_test_db_env(monkeypatch)
    init_db_schema()
    clear_event_tables()

    conn = connect()
    try:
        insert_signal(
            strategy="Ott2butKAMA",
            symbol="ETHUSDT",
            timeframe="5m",
            signal_time=datetime.now(timezone.utc).isoformat(),
            action="open_long",
            payload={"source": "test"},
        )

        run_once()

        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT status FROM signal_events ORDER BY id DESC LIMIT 1")
                signal_row = cur.fetchone()
                assert signal_row is not None
                signal_status = signal_row[0]

                cur.execute("SELECT status FROM execution_events ORDER BY id DESC LIMIT 1")
                execution_row = cur.fetchone()
                assert execution_row is not None
                execution_status = execution_row[0]

        assert signal_status == "execute"
        assert execution_status == "execute"
    finally:
        conn.close()
