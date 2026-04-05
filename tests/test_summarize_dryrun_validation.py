from datetime import datetime, timedelta, timezone
import os
import subprocess
import sys
from pathlib import Path

import pytest


def test_render_summary_includes_counts_and_latest_timestamps():
    from scripts.summarize_dryrun_validation import render_summary

    summary = {
        "window_minutes": 60,
        "signal_count": 12,
        "execution_count": 10,
        "signal_status_counts": {"execute": 8, "ignored": 3, "rejected": 1},
        "latest_signal_time": datetime(2026, 4, 5, 3, 0, tzinfo=timezone.utc),
        "latest_execution_time": datetime(2026, 4, 5, 3, 2, tzinfo=timezone.utc),
    }

    text = render_summary(summary)

    assert "window_minutes: 60" in text
    assert "signal_count: 12" in text
    assert "execution_count: 10" in text
    assert "execute: 8" in text
    assert "ignored: 3" in text
    assert "rejected: 1" in text
    assert "latest_signal_time: 2026-04-05T03:00:00+00:00" in text
    assert "latest_execution_time: 2026-04-05T03:02:00+00:00" in text


def test_window_start_uses_minutes_offset():
    from scripts.summarize_dryrun_validation import build_window_start

    now = datetime(2026, 4, 5, 4, 0, tzinfo=timezone.utc)

    assert build_window_start(now=now, minutes=90) == now - timedelta(minutes=90)


def test_render_summary_handles_missing_latest_timestamps():
    from scripts.summarize_dryrun_validation import render_summary

    summary = {
        "window_minutes": 60,
        "signal_count": 0,
        "execution_count": 0,
        "signal_status_counts": {},
        "latest_signal_time": None,
        "latest_execution_time": None,
    }

    text = render_summary(summary)

    assert "latest_signal_time: none" in text
    assert "latest_execution_time: none" in text


def test_parse_args_rejects_non_positive_minutes(monkeypatch: pytest.MonkeyPatch):
    from scripts.summarize_dryrun_validation import parse_args

    monkeypatch.setattr("sys.argv", ["summarize_dryrun_validation.py", "--minutes", "0"])

    with pytest.raises(SystemExit):
        parse_args()


def test_parse_args_accepts_positive_minutes(monkeypatch: pytest.MonkeyPatch):
    from scripts.summarize_dryrun_validation import parse_args

    monkeypatch.setattr("sys.argv", ["summarize_dryrun_validation.py", "--minutes", "60"])

    assert parse_args().minutes == 60


def test_summary_script_runs_directly_without_pythonpath_env():
    repo_root = Path(__file__).resolve().parent.parent
    script = repo_root / "scripts" / "summarize_dryrun_validation.py"
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.update(
        {
            "POSTGRES_HOST": "127.0.0.1",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "jesse_db",
            "POSTGRES_USER": "jesse_user",
            "POSTGRES_PASSWORD": "password",
        }
    )

    completed = subprocess.run(
        [sys.executable, str(script), "--minutes", "60"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "signal_count:" in completed.stdout
    assert "execution_count:" in completed.stdout
