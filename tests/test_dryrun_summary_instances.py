import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_render_summary_includes_instance_rollups():
    from scripts.summarize_dryrun_validation import render_summary

    summary = {
        "window_minutes": 60,
        "signal_count": 3,
        "execution_count": 2,
        "signal_status_counts": {"execute": 2, "ignored": 1},
        "latest_signal_time": None,
        "latest_execution_time": None,
        "instances": {
            "ott_eth_5m": {"signal_count": 2, "execution_count": 1},
            "risk25_sol_5m": {"signal_count": 1, "execution_count": 1},
        },
    }

    text = render_summary(summary)

    assert "instance: ott_eth_5m signal_count=2 execution_count=1" in text
    assert "instance: risk25_sol_5m signal_count=1 execution_count=1" in text


def test_render_summary_sorts_instance_rollups():
    from scripts.summarize_dryrun_validation import render_summary

    summary = {
        "window_minutes": 60,
        "signal_count": 3,
        "execution_count": 2,
        "signal_status_counts": {"execute": 2, "ignored": 1},
        "latest_signal_time": None,
        "latest_execution_time": None,
        "instances": {
            "z_last": {"signal_count": 1, "execution_count": 0},
            "a_first": {"signal_count": 2, "execution_count": 2},
        },
    }

    lines = render_summary(summary).splitlines()

    assert lines[-2] == "instance: a_first signal_count=2 execution_count=2"
    assert lines[-1] == "instance: z_last signal_count=1 execution_count=0"


def test_fetch_summary_returns_instance_rollups(monkeypatch):
    from scripts import summarize_dryrun_validation as module

    class FakeInstance:
        def __init__(self, instance_id):
            self.id = instance_id

    class FakeCursor:
        def __init__(self):
            self._fetchone_results = iter(
                [
                    (3, datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc)),
                    (2, datetime(2026, 4, 15, 12, 1, tzinfo=timezone.utc)),
                ]
            )
            self._fetchall_results = iter(
                [
                    [("execute", 2), ("ignored", 1)],
                    [("ott_eth_5m", 2), ("risk25_sol_5m", 1)],
                    [("ott_eth_5m", 1), ("risk25_sol_5m", 1)],
                ]
            )

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params):
            self.last_query = query
            self.last_params = params

        def fetchone(self):
            return next(self._fetchone_results)

        def fetchall(self):
            return next(self._fetchall_results)

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return FakeCursor()

        def close(self):
            pass

    monkeypatch.setattr(module, "connect", lambda: FakeConnection())
    monkeypatch.setattr(
        module,
        "load_instances",
        lambda config_path: [FakeInstance("ott_eth_5m"), FakeInstance("risk25_sol_5m")],
    )

    summary = module.fetch_summary(minutes=60)

    assert summary["instances"] == {
        "ott_eth_5m": {"signal_count": 2, "execution_count": 1},
        "risk25_sol_5m": {"signal_count": 1, "execution_count": 1},
    }


def test_render_summary_includes_enabled_instance_with_zero_activity(monkeypatch):
    from scripts import summarize_dryrun_validation as module

    class FakeInstance:
        def __init__(self, instance_id):
            self.id = instance_id

    class FakeCursor:
        def __init__(self):
            self._fetchone_results = iter(
                [
                    (1, datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc)),
                    (1, datetime(2026, 4, 15, 12, 1, tzinfo=timezone.utc)),
                ]
            )
            self._fetchall_results = iter(
                [
                    [("execute", 1)],
                    [("ott_eth_5m", 1)],
                    [("ott_eth_5m", 1)],
                ]
            )

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params):
            self.last_query = query
            self.last_params = params

        def fetchone(self):
            return next(self._fetchone_results)

        def fetchall(self):
            return next(self._fetchall_results)

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return FakeCursor()

        def close(self):
            pass

    monkeypatch.setattr(module, "connect", lambda: FakeConnection())
    monkeypatch.setattr(
        module,
        "load_instances",
        lambda config_path: [FakeInstance("ott_eth_5m"), FakeInstance("risk25_sol_5m")],
    )

    summary = module.fetch_summary(minutes=60)
    text = module.render_summary(summary)

    assert summary["instances"] == {
        "ott_eth_5m": {"signal_count": 1, "execution_count": 1},
        "risk25_sol_5m": {"signal_count": 0, "execution_count": 0},
    }
    assert "instance: risk25_sol_5m signal_count=0 execution_count=0" in text
