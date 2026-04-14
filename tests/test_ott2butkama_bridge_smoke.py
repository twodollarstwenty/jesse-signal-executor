import os

import pytest
from psycopg2.extras import RealDictCursor

from apps.executor_service.service import run_once
from apps.shared.db import connect
from apps.signal_service.jesse_bridge.emitter import emit_signal
from tests.db_testkit import apply_test_db_env, clear_event_tables, init_db_schema


def _rows_for_test_case(*, strategy: str, symbol: str, timeframe: str, signal_time: str, action: str) -> tuple[list[dict], list[dict]]:
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
                    """
                    ,
                    (strategy, symbol, timeframe, signal_time, action),
                )
                signals = cur.fetchall()

                if len(signals) != 1:
                    return signals, []

                cur.execute(
                    """
                    SELECT id, signal_id, symbol, mode, status
                    FROM execution_events
                    WHERE signal_id = %s
                    ORDER BY id DESC
                    """
                    ,
                    (signals[0]["id"],),
                )
                executions = cur.fetchall()
        return signals, executions
    finally:
        conn.close()


def test_bridge_execute_path_end_to_end():
    if os.getenv("PYTEST_XDIST_WORKER"):
        pytest.skip("uses clear_event_tables on shared tables; run without xdist workers")

    apply_test_db_env()
    init_db_schema()
    clear_event_tables()

    strategy = "Ott2butKAMA"
    symbol = "ETHUSDT"
    timeframe = "5m"
    signal_time = "2024-04-04T00:00:00Z"
    action = "open_long"

    emit_signal(
        instance_id="ott_eth_5m",
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        candle_timestamp=1712188800000,
        action=action,
        payload={"source": "smoke-test", "price": 2500.0},
    )

    run_once()

    signals, executions = _rows_for_test_case(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        signal_time=signal_time,
        action=action,
    )

    assert len(signals) == 1, f"expected exactly one matching signal row, got {len(signals)}: {signals}"
    signal = signals[0]

    assert signal["strategy"] == strategy, signal
    assert signal["symbol"] == symbol, signal
    assert signal["action"] == action, signal
    assert signal["status"] == "execute", signal

    assert len(executions) == 1, f"expected exactly one linked execution row, got {len(executions)}: {executions}"
    execution = executions[0]

    assert execution["symbol"] == symbol, execution
    assert execution["mode"] == "dry_run", execution
    assert execution["status"] == "execute", execution
    assert execution["signal_id"] == signal["id"], {"signal": signal, "execution": execution}
