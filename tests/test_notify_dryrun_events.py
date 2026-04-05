import os
import subprocess
import sys
from pathlib import Path


def test_format_execution_event_message_contains_core_fields():
    from scripts.notify_dryrun_events import format_execution_event_message

    row = {
        "created_at": "2026-04-05T12:35:00+08:00",
        "strategy": "Ott2butKAMA_RiskManaged25",
        "symbol": "ETHUSDT",
        "action": "open_long",
        "decision": "execute",
        "reason": None,
    }

    text = format_execution_event_message(row)

    assert "[Dry-Run]" in text
    assert "策略: Ott2butKAMA_RiskManaged25" in text
    assert "动作: open_long" in text
    assert "处理结果: execute" in text


def test_format_execution_event_message_supports_joined_signal_fields():
    from scripts.notify_dryrun_events import format_execution_event_message

    row = {
        "created_at": "2026-04-05T17:13:50+08:00",
        "strategy": "Ott2butKAMA",
        "symbol": "ETHUSDT",
        "action": "close_long",
        "decision": "execute",
        "reason": None,
    }

    text = format_execution_event_message(row)

    assert "策略: Ott2butKAMA" in text
    assert "交易对: ETHUSDT" in text
    assert "动作: close_long" in text
    assert "处理结果: execute" in text


def test_format_execution_event_message_includes_signal_and_execution_context():
    from scripts.notify_dryrun_events import format_execution_event_message

    row = {
        "signal_time": "2024-04-04T08:00:00+08:00",
        "created_at": "2026-04-05T17:13:50+08:00",
        "strategy": "Ott2butKAMA",
        "symbol": "ETHUSDT",
        "action": "close_long",
        "decision": "execute",
        "reason": None,
        "price": 2500.0,
        "position_side": "long",
    }

    text = format_execution_event_message(row)

    assert "信号时间: 2024-04-04T08:00:00+08:00" in text
    assert "执行时间: 2026-04-05T17:13:50+08:00" in text
    assert "价格: 2500.0" in text
    assert "仓位方向: long" in text


def test_format_backtest_summary_message_contains_key_metrics():
    from apps.notifications.wecom import format_backtest_summary_message

    text = format_backtest_summary_message(
        baseline="Ott2butKAMA",
        candidate="Ott2butKAMA_RiskManaged25",
        symbol="ETHUSDT",
        timeframe="5m",
        window="2025-10-05 -> 2026-04-05",
        trades="93",
        win_rate="43.01%",
        net_profit="94.26%",
        max_drawdown="-20.12%",
    )

    assert "[回测结果]" in text
    assert "候选策略: Ott2butKAMA_RiskManaged25" in text
    assert "净收益: 94.26%" in text


def test_notify_dryrun_events_runs_directly_from_repo_root_without_pythonpath_env():
    repo_root = Path(__file__).resolve().parent.parent
    script = repo_root / "scripts" / "notify_dryrun_events.py"
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.update(
        {
            "POSTGRES_HOST": "127.0.0.1",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "jesse_db",
            "POSTGRES_USER": "jesse_user",
            "POSTGRES_PASSWORD": "password",
            "NOTIFY_ENABLED": "0",
        }
    )

    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_fetch_recent_execution_events_joins_signal_fields(monkeypatch):
    from scripts.notify_dryrun_events import fetch_recent_execution_events

    rows = [
        (
            "2026-04-05T17:13:50+08:00",
            "2024-04-04T08:00:00+08:00",
            "Ott2butKAMA",
            "ETHUSDT",
            "close_long",
            "execute",
            None,
            {},
        )
    ]

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params):
            self.query = query
            self.params = params

        def fetchall(self):
            return rows

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return FakeCursor()

        def close(self):
            return None

    monkeypatch.setattr("scripts.notify_dryrun_events.connect", lambda: FakeConnection())

    events = fetch_recent_execution_events(limit=5)

    assert events == [
        {
            "created_at": "2026-04-05T17:13:50+08:00",
            "signal_time": "2024-04-04T08:00:00+08:00",
            "strategy": "Ott2butKAMA",
            "symbol": "ETHUSDT",
            "action": "close_long",
            "decision": "execute",
            "reason": None,
            "price": "N/A",
            "position_side": "N/A",
        }
    ]


def test_fetch_recent_execution_events_extracts_price_and_position_side(monkeypatch):
    from scripts.notify_dryrun_events import fetch_recent_execution_events

    rows = [
        (
            "2026-04-05T17:13:50+08:00",
            "2024-04-04T08:00:00+08:00",
            "Ott2butKAMA",
            "ETHUSDT",
            "close_long",
            "execute",
            None,
            {"price": 2500.0, "position_side": "long"},
        )
    ]

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params):
            self.query = query
            self.params = params

        def fetchall(self):
            return rows

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return FakeCursor()

        def close(self):
            return None

    monkeypatch.setattr("scripts.notify_dryrun_events.connect", lambda: FakeConnection())

    events = fetch_recent_execution_events(limit=5)

    assert events == [
        {
            "created_at": "2026-04-05T17:13:50+08:00",
            "signal_time": "2024-04-04T08:00:00+08:00",
            "strategy": "Ott2butKAMA",
            "symbol": "ETHUSDT",
            "action": "close_long",
            "decision": "execute",
            "reason": None,
            "price": 2500.0,
            "position_side": "long",
        }
    ]
