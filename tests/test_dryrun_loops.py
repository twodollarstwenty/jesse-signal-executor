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


def test_write_heartbeat_recovers_if_temp_file_disappears_before_replace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from scripts.run_executor_loop import write_heartbeat

    heartbeat_path = tmp_path / "executor.heartbeat"
    original_replace = Path.replace
    replace_calls = {"count": 0}

    def flaky_replace(self: Path, target: Path):
        replace_calls["count"] += 1
        if replace_calls["count"] == 1:
            if self.exists():
                self.unlink()
            raise FileNotFoundError("simulated tmp file race")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", flaky_replace)

    write_heartbeat(heartbeat_path)

    assert heartbeat_path.exists()
    parsed = datetime.fromisoformat(heartbeat_path.read_text().strip())
    assert parsed.tzinfo is not None


def test_write_heartbeat_retries_multiple_replace_races_before_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from scripts.run_executor_loop import write_heartbeat

    heartbeat_path = tmp_path / "executor.heartbeat"
    original_replace = Path.replace
    replace_calls = {"count": 0}

    def flaky_replace(self: Path, target: Path):
        replace_calls["count"] += 1
        if replace_calls["count"] <= 2:
            if self.exists():
                self.unlink()
            raise FileNotFoundError("simulated repeated tmp file race")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", flaky_replace)

    write_heartbeat(heartbeat_path)

    assert heartbeat_path.exists()
    parsed = datetime.fromisoformat(heartbeat_path.read_text().strip())
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
    sync_calls: list[str] = []

    def fake_run(args: list[str], check: bool) -> None:
        calls.append((args, check))

    def fake_sleep(interval: float) -> None:
        calls.append(interval)
        raise StopLoop

    monkeypatch.setenv("JESSE_HEARTBEAT_PATH", str(heartbeat_path))
    monkeypatch.setenv("JESSE_DRYRUN_INTERVAL_SECONDS", "7.5")
    monkeypatch.setenv("JESSE_DRYRUN_COMMAND", "python3 scripts/verify_jesse_imports.py --flag")
    monkeypatch.setenv("DRYRUN_STRATEGY_NAME", "StandardGrid_LightMartingale_v1")
    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(module.time, "sleep", fake_sleep)
    monkeypatch.setattr(module, "sync_strategy", lambda name: sync_calls.append(name))

    with pytest.raises(StopLoop):
        module.main()

    assert sync_calls == ["StandardGrid_LightMartingale_v1"]
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


def test_classify_runtime_decision_marks_duplicate_action_as_suppressed():
    import scripts.run_jesse_live_loop as module

    outcome = module.classify_runtime_decision(
        proposed_action="open_long",
        should_emit_before_runtime_gates=True,
        strategy_reason_code="entry_signal_emitted",
        persistent_position=None,
        remembered_action="open_long",
    )

    assert outcome == {
        "final_action": "none",
        "emitted": False,
        "decision_status": "suppressed_duplicate",
        "reason_code": "duplicate_action",
    }


def test_run_cycle_persists_decision_trace_for_processed_candle(tmp_path, monkeypatch):
    import contextlib
    import scripts.run_jesse_live_loop as module

    calls = []
    context = {
        "instance_id": "ott_eth_5m",
        "strategy_name": "StandardGrid_LightMartingale_v1",
        "symbol": "ETH-USDT",
        "timeframe": "5m",
        "capital_usdt": 1000.0,
        "paths": {
            "last_action": tmp_path / "last_action.txt",
            "last_candle": tmp_path / "last_candle.txt",
        },
    }
    snapshot = {
        "timestamp": "2026-04-30T12:55:00+00:00",
        "latest_timestamp": 1714481700000,
        "close_prices": [2300.0, 2280.0, 2240.0],
    }

    @contextlib.contextmanager
    def fake_workspace_cwd(workspace):
        yield

    monkeypatch.setattr(module, "ensure_runtime_ready", lambda: tmp_path)
    monkeypatch.setattr(module, "prepare_import_path", lambda workspace: None)
    monkeypatch.setattr(module, "workspace_cwd", fake_workspace_cwd)
    monkeypatch.setattr(module, "fetch_recent_klines", lambda symbol, interval: snapshot)
    monkeypatch.setattr(module, "fetch_persistent_position", lambda symbol, instance_id=None: None)
    monkeypatch.setattr(module, "read_last_processed_candle_ts", lambda context=None: 1714481400000)
    monkeypatch.setattr(module, "get_in_memory_last_processed_candle_ts", lambda context=None: 1714481400000)
    monkeypatch.setattr(module, "set_in_memory_last_processed_candle_ts", lambda value, context=None: None)
    monkeypatch.setattr(module, "write_last_processed_candle_ts", lambda value, context=None: None)
    monkeypatch.setattr(module, "read_last_emitted_action", lambda context=None: None)
    monkeypatch.setattr(module, "get_in_memory_last_emitted_action", lambda context=None: None)
    monkeypatch.setattr(module, "set_in_memory_last_emitted_action", lambda action, context=None: None)
    monkeypatch.setattr(module, "write_last_emitted_action", lambda action, context=None: None)
    monkeypatch.setattr(module, "print_cycle_summary", lambda loop_state, context=None: None)
    monkeypatch.setattr(
        module,
        "build_strategy_runtime_trace",
        lambda context, loop_state, persistent_position: {
            "market": {"candle_timestamp": 1714481700000, "price": 2240.0},
            "box": {},
            "grid": {},
            "sizing": {},
            "inventory": {},
            "strategy_decision": {
                "intent": "long",
                "proposed_action": "open_long",
                "should_emit_before_runtime_gates": True,
                "reason_code": "entry_signal_emitted",
                "reason_text": "price reached the next eligible grid level",
                "signal_payload_preview": {"source": "jesse", "price": 2240.0, "position_side": "long", "qty": 0.02},
            },
        },
    )
    monkeypatch.setattr(module, "emit_strategy_signals", lambda context, loop_state=None: {**loop_state, "emitted": True})
    monkeypatch.setattr(module, "insert_signal_decision", lambda **kwargs: calls.append(kwargs))

    module.run_cycle(context)

    assert calls[0]["instance_id"] == "ott_eth_5m"
    assert calls[0]["strategy"] == "StandardGrid_LightMartingale_v1"
    assert calls[0]["intent"] == "long"
    assert calls[0]["action"] == "open_long"
    assert calls[0]["emitted"] is True
    assert calls[0]["decision_status"] == "emitted"
    assert calls[0]["reason_code"] == "entry_signal_emitted"


def test_classify_runtime_decision_marks_close_without_position_as_skipped():
    import scripts.run_jesse_live_loop as module

    outcome = module.classify_runtime_decision(
        proposed_action="close_long",
        should_emit_before_runtime_gates=True,
        strategy_reason_code="exit_signal_emitted",
        persistent_position=None,
        remembered_action=None,
    )

    assert outcome == {
        "final_action": "none",
        "emitted": False,
        "decision_status": "skipped_no_position",
        "reason_code": "no_position_to_close",
    }


def test_classify_runtime_decision_keeps_strategy_noop_reason():
    import scripts.run_jesse_live_loop as module

    outcome = module.classify_runtime_decision(
        proposed_action="none",
        should_emit_before_runtime_gates=False,
        strategy_reason_code="box_not_confirmed",
        persistent_position=None,
        remembered_action=None,
    )

    assert outcome == {
        "final_action": "none",
        "emitted": False,
        "decision_status": "noop",
        "reason_code": "box_not_confirmed",
    }
