from apps.shared.db import connect
from tests.db_testkit import apply_test_db_env, clear_event_tables, init_db_schema


def test_init_db_schema_adds_instance_id_columns(monkeypatch):
    apply_test_db_env(monkeypatch)
    init_db_schema()
    clear_event_tables()

    conn = connect()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name IN ('signal_events', 'execution_events', 'position_state')
                  AND column_name = 'instance_id'
                ORDER BY table_name
                """
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    assert rows == [
        ("execution_events", "instance_id"),
        ("position_state", "instance_id"),
        ("signal_events", "instance_id"),
    ]
