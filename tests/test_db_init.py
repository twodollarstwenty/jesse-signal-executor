from pathlib import Path


def test_db_init_sql_contains_core_tables():
    sql = Path("db/init.sql").read_text()
    assert "CREATE TABLE IF NOT EXISTS signal_events" in sql
    assert "CREATE TABLE IF NOT EXISTS execution_events" in sql
    assert "CREATE TABLE IF NOT EXISTS position_state" in sql
