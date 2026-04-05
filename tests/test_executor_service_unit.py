from apps.executor_service.service import build_execution_payload


def test_build_execution_payload_uses_dry_run_mode():
    payload = build_execution_payload(signal_id=1, symbol="ETHUSDT", status="execute")
    assert payload["signal_id"] == 1
    assert payload["mode"] == "dry_run"
    assert payload["status"] == "execute"


def test_build_position_payload_persists_qty_and_entry_price_for_open_position():
    from apps.executor_service.service import build_position_payload

    payload = build_position_payload(
        symbol="ETHUSDT",
        side="long",
        signal_payload={"price": 2450.0, "qty": 2.5},
    )

    assert payload == {
        "symbol": "ETHUSDT",
        "side": "long",
        "qty": 2.5,
        "entry_price": 2450.0,
        "state_json": {},
    }


def test_build_position_payload_resets_qty_and_entry_for_flat_state():
    from apps.executor_service.service import build_position_payload

    payload = build_position_payload(
        symbol="ETHUSDT",
        side="flat",
        signal_payload={"price": 2450.0, "qty": 2.5},
    )

    assert payload == {
        "symbol": "ETHUSDT",
        "side": "flat",
        "qty": 0.0,
        "entry_price": 0.0,
        "state_json": {},
    }
