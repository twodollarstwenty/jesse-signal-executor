from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


def test_write_heartbeat_updates_timestamp_file(tmp_path: Path):
    from scripts.run_executor_loop import write_heartbeat

    heartbeat_path = tmp_path / "executor.heartbeat"
    write_heartbeat(heartbeat_path)

    assert heartbeat_path.exists()
    text = heartbeat_path.read_text().strip()
    parsed = datetime.fromisoformat(text)
    assert parsed.tzinfo is not None


def test_check_heartbeat_returns_true_for_recent_file(tmp_path: Path):
    from scripts.check_heartbeat import is_healthy
    from scripts.run_executor_loop import write_heartbeat

    heartbeat_path = tmp_path / "executor.heartbeat"
    write_heartbeat(heartbeat_path)

    assert is_healthy(heartbeat_path, max_age_seconds=60) is True


def test_check_heartbeat_returns_false_for_missing_file(tmp_path: Path):
    from scripts.check_heartbeat import is_healthy

    assert is_healthy(tmp_path / "missing.heartbeat", max_age_seconds=60) is False


def test_check_heartbeat_returns_false_when_timestamp_exceeds_max_age(tmp_path: Path):
    from scripts.check_heartbeat import is_healthy

    heartbeat_path = tmp_path / "executor.heartbeat"
    stale_timestamp = datetime.now(timezone.utc) - timedelta(seconds=61)
    heartbeat_path.write_text(stale_timestamp.isoformat())

    assert is_healthy(heartbeat_path, max_age_seconds=60) is False


def test_check_heartbeat_returns_false_for_invalid_timestamp(tmp_path: Path):
    from scripts.check_heartbeat import is_healthy

    heartbeat_path = tmp_path / "executor.heartbeat"
    heartbeat_path.write_text("not-an-iso-timestamp")

    assert is_healthy(heartbeat_path, max_age_seconds=60) is False


def test_check_heartbeat_returns_false_on_oserror(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from scripts.check_heartbeat import is_healthy

    heartbeat_path = tmp_path / "executor.heartbeat"
    heartbeat_path.write_text(datetime.now(timezone.utc).isoformat())

    def raising_read_text(self: Path, *args, **kwargs):
        raise OSError("simulated read race")

    monkeypatch.setattr(Path, "read_text", raising_read_text)

    assert is_healthy(heartbeat_path, max_age_seconds=60) is False


def test_run_executor_loop_main_uses_env_heartbeat_and_interval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import scripts.run_executor_loop as module

    class StopLoop(Exception):
        pass

    heartbeat_path = tmp_path / "custom-executor.heartbeat"
    calls: list[str] = []

    def fake_run_once() -> None:
        calls.append("run_once")

    def fake_sleep(interval: float) -> None:
        calls.append(f"sleep:{interval}")
        raise StopLoop

    monkeypatch.setenv("EXECUTOR_HEARTBEAT_PATH", str(heartbeat_path))
    monkeypatch.setenv("EXECUTOR_POLL_INTERVAL_SECONDS", "2.5")
    monkeypatch.setattr(module, "run_once", fake_run_once)
    monkeypatch.setattr(module.time, "sleep", fake_sleep)

    with pytest.raises(StopLoop):
        module.main()

    assert calls == ["run_once", "sleep:2.5"]
    assert heartbeat_path.exists()


@pytest.mark.parametrize("raw_value", ["0", "-1", "nan", "inf", "abc"])
def test_run_executor_loop_main_rejects_invalid_interval(
    monkeypatch: pytest.MonkeyPatch, raw_value: str
):
    import scripts.run_executor_loop as module

    monkeypatch.setenv("EXECUTOR_POLL_INTERVAL_SECONDS", raw_value)

    with pytest.raises(ValueError, match="EXECUTOR_POLL_INTERVAL_SECONDS"):
        module.main()


def test_run_jesse_dryrun_loop_main_uses_env_heartbeat_interval_and_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import scripts.run_jesse_dryrun_loop as module

    class StopLoop(Exception):
        pass

    heartbeat_path = tmp_path / "custom-jesse.heartbeat"
    calls: list[object] = []

    def fake_run(args: list[str], check: bool) -> None:
        calls.append((args, check))

    def fake_sleep(interval: float) -> None:
        calls.append(interval)
        raise StopLoop

    monkeypatch.setenv("JESSE_HEARTBEAT_PATH", str(heartbeat_path))
    monkeypatch.setenv("JESSE_DRYRUN_INTERVAL_SECONDS", "7.5")
    monkeypatch.setenv("JESSE_DRYRUN_COMMAND", "python3 scripts/verify_jesse_imports.py --flag")
    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(module.time, "sleep", fake_sleep)

    with pytest.raises(StopLoop):
        module.main()

    assert calls == [(["python3", "scripts/verify_jesse_imports.py", "--flag"], True), 7.5]
    assert heartbeat_path.exists()


def test_run_jesse_dryrun_loop_main_uses_live_loop_default_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import scripts.run_jesse_dryrun_loop as module

    class StopLoop(Exception):
        pass

    heartbeat_path = tmp_path / "default-jesse.heartbeat"
    calls: list[object] = []

    def fake_run(args: list[str], check: bool) -> None:
        calls.append((args, check))

    def fake_sleep(interval: float) -> None:
        calls.append(interval)
        raise StopLoop

    monkeypatch.setenv("JESSE_HEARTBEAT_PATH", str(heartbeat_path))
    monkeypatch.delenv("JESSE_DRYRUN_COMMAND", raising=False)
    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(module.time, "sleep", fake_sleep)

    with pytest.raises(StopLoop):
        module.main()

    expected_script = str((Path(module.__file__).resolve().parent / "run_jesse_live_loop.py").resolve())

    assert calls == [(["python3", expected_script], True), 10.0]
    assert heartbeat_path.exists()


@pytest.mark.parametrize("raw_value", ["0", "-1", "nan", "inf", "abc"])
def test_run_jesse_dryrun_loop_main_rejects_invalid_interval(
    monkeypatch: pytest.MonkeyPatch, raw_value: str
):
    import scripts.run_jesse_dryrun_loop as module

    monkeypatch.setenv("JESSE_DRYRUN_INTERVAL_SECONDS", raw_value)

    with pytest.raises(ValueError, match="JESSE_DRYRUN_INTERVAL_SECONDS"):
        module.main()
