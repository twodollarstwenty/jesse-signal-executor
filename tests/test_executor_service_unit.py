from apps.executor_service.service import build_execution_payload


def test_build_execution_payload_uses_dry_run_mode():
    payload = build_execution_payload(signal_id=1, symbol="ETHUSDT", status="execute")
    assert payload["signal_id"] == 1
    assert payload["mode"] == "dry_run"
    assert payload["status"] == "execute"
