import os
from pathlib import Path

from apps.shared.db import connect


TEST_DB_ENV = {
    "POSTGRES_HOST": "127.0.0.1",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "jesse_db",
    "POSTGRES_USER": "jesse_user",
    "POSTGRES_PASSWORD": "password",
}


def apply_test_db_env(monkeypatch=None) -> None:
    if monkeypatch is None:
        os.environ.update(TEST_DB_ENV)
        return

    for key, value in TEST_DB_ENV.items():
        monkeypatch.setenv(key, value)


def init_db_schema() -> None:
    sql = (Path(__file__).resolve().parent.parent / "db" / "init.sql").read_text()
    conn = connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql)
    finally:
        conn.close()


def clear_event_tables() -> None:
    conn = connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM execution_events")
                cur.execute("DELETE FROM signal_events")
                cur.execute("DELETE FROM position_state")
    finally:
        conn.close()
