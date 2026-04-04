import os

import pytest
from psycopg2.extras import RealDictCursor

from apps.executor_service.service import run_once
from apps.shared.db import connect
from apps.signal_service.writer import insert_signal
from tests.db_testkit import apply_test_db_env, clear_event_tables, init_db_schema


def _insert_position_side(*, symbol: str, side: str) -> None:
    conn = connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO position_state (symbol, side, qty, entry_price, state_json)
                    VALUES (%s, %s, %s, %s, %s::jsonb)
                    """,
                    (symbol, side, 1, 2500, "{}"),
                )
    finally:
        conn.close()


def _fetch_signal_and_execution(*, strategy: str, symbol: str, timeframe: str, signal_time: str, action: str) -> tuple[dict, dict]:
    conn = connect()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, strategy, symbol, action, status
                    FROM signal_events
                    WHERE strategy = %s
                      AND symbol = %s
                      AND timeframe = %s
                      AND signal_time = %s::timestamptz
                      AND action = %s
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (strategy, symbol, timeframe, signal_time, action),
                )
                signal = cur.fetchone()

                assert signal is not None, "signal row not found for test case"

                cur.execute("SELECT COUNT(*) FROM execution_events WHERE signal_id = %s", (signal["id"],))
                execution_count = cur.fetchone()["count"]
                assert execution_count == 1, {"signal_id": signal["id"], "execution_count": execution_count}

                cur.execute(
                    """
                    SELECT id, signal_id, symbol, mode, status
                    FROM execution_events
                    WHERE signal_id = %s
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (signal["id"],),
                )
                execution = cur.fetchone()

                assert execution is not None, "execution row not found for test case"
                return signal, execution
    finally:
        conn.close()


def test_open_long_ignored_when_current_side_is_long(monkeypatch):
    if os.getenv("PYTEST_XDIST_WORKER"):
        pytest.skip("uses clear_event_tables on shared tables; run without xdist workers")

    apply_test_db_env(monkeypatch)
    init_db_schema()
    clear_event_tables()

    strategy = "Ott2butKAMA"
    symbol = "ETHUSDT"
    timeframe = "5m"
    signal_time = "2024-04-05T00:00:00Z"
    action = "open_long"

    _insert_position_side(symbol=symbol, side="long")

    insert_signal(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        signal_time=signal_time,
        action=action,
        payload={"source": "ignored-e2e"},
    )

    run_once()

    signal, execution = _fetch_signal_and_execution(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        signal_time=signal_time,
        action=action,
    )

    assert signal["status"] == "ignored", signal
    assert execution["status"] == "ignored", execution
    assert execution["mode"] == "dry_run", execution
    assert execution["signal_id"] == signal["id"], {"signal": signal, "execution": execution}


def test_open_long_rejected_when_current_side_is_short(monkeypatch):
    if os.getenv("PYTEST_XDIST_WORKER"):
        pytest.skip("uses clear_event_tables on shared tables; run without xdist workers")

    apply_test_db_env(monkeypatch)
    init_db_schema()
    clear_event_tables()

    strategy = "Ott2butKAMA"
    symbol = "ETHUSDT"
    timeframe = "5m"
    signal_time = "2024-04-05T00:05:00Z"
    action = "open_long"

    _insert_position_side(symbol=symbol, side="short")

    insert_signal(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        signal_time=signal_time,
        action=action,
        payload={"source": "rejected-e2e"},
    )

    run_once()

    signal, execution = _fetch_signal_and_execution(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        signal_time=signal_time,
        action=action,
    )

    assert signal["status"] == "rejected", signal
    assert execution["status"] == "rejected", execution
    assert execution["mode"] == "dry_run", execution
    assert execution["signal_id"] == signal["id"], {"signal": signal, "execution": execution}


def test_open_short_ignored_when_current_side_is_short(monkeypatch):
    if os.getenv("PYTEST_XDIST_WORKER"):
        pytest.skip("uses clear_event_tables on shared tables; run without xdist workers")

    apply_test_db_env(monkeypatch)
    init_db_schema()
    clear_event_tables()

    strategy = "Ott2butKAMA"
    symbol = "ETHUSDT"
    timeframe = "5m"
    signal_time = "2024-04-05T00:10:00Z"
    action = "open_short"

    _insert_position_side(symbol=symbol, side="short")

    insert_signal(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        signal_time=signal_time,
        action=action,
        payload={"source": "ignored-open-short-e2e"},
    )

    run_once()

    signal, execution = _fetch_signal_and_execution(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        signal_time=signal_time,
        action=action,
    )

    assert signal["status"] == "ignored", signal
    assert execution["status"] == "ignored", execution
    assert execution["mode"] == "dry_run", execution
    assert execution["signal_id"] == signal["id"], {"signal": signal, "execution": execution}


def test_open_short_rejected_when_current_side_is_long(monkeypatch):
    if os.getenv("PYTEST_XDIST_WORKER"):
        pytest.skip("uses clear_event_tables on shared tables; run without xdist workers")

    apply_test_db_env(monkeypatch)
    init_db_schema()
    clear_event_tables()

    strategy = "Ott2butKAMA"
    symbol = "ETHUSDT"
    timeframe = "5m"
    signal_time = "2024-04-05T00:15:00Z"
    action = "open_short"

    _insert_position_side(symbol=symbol, side="long")

    insert_signal(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        signal_time=signal_time,
        action=action,
        payload={"source": "rejected-open-short-e2e"},
    )

    run_once()

    signal, execution = _fetch_signal_and_execution(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        signal_time=signal_time,
        action=action,
    )

    assert signal["status"] == "rejected", signal
    assert execution["status"] == "rejected", execution
    assert execution["mode"] == "dry_run", execution
    assert execution["signal_id"] == signal["id"], {"signal": signal, "execution": execution}
