import importlib


def test_connect_uses_local_repo_defaults_when_env_unset(monkeypatch):
    import apps.shared.db as module

    for key in ("POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"):
        monkeypatch.delenv(key, raising=False)

    captured = {}

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(module.psycopg2, "connect", fake_connect)
    importlib.reload(module)

    module.connect()

    assert captured == {
        "host": "127.0.0.1",
        "port": 5432,
        "dbname": "jesse_db",
        "user": "jesse_user",
        "password": "password",
    }
