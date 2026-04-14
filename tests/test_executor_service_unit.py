from apps.executor_service.service import build_execution_payload


class RecordingCursor:
    def __init__(self, row=None):
        self.row = row
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchone(self):
        return self.row


def test_build_execution_payload_keeps_instance_id_and_dry_run_mode():
    payload = build_execution_payload(instance_id="ott_eth_5m", signal_id=1, symbol="ETHUSDT", status="execute")

    assert payload["instance_id"] == "ott_eth_5m"
    assert payload["signal_id"] == 1
    assert payload["mode"] == "dry_run"
    assert payload["status"] == "execute"
    assert payload["detail_json"] == {"source": "executor_service"}


def test_build_position_payload_persists_instance_id_qty_and_entry_price_for_open_position():
    from apps.executor_service.service import build_position_payload

    payload = build_position_payload(
        instance_id="ott_eth_5m",
        symbol="ETHUSDT",
        side="long",
        signal_payload={"price": 2450.0, "qty": 2.5},
    )

    assert payload == {
        "instance_id": "ott_eth_5m",
        "symbol": "ETHUSDT",
        "side": "long",
        "qty": 2.5,
        "entry_price": 2450.0,
        "state_json": {},
    }


def test_build_position_payload_keeps_instance_id_for_flat_state():
    from apps.executor_service.service import build_position_payload

    payload = build_position_payload(
        instance_id="ott_eth_5m",
        symbol="ETHUSDT",
        side="flat",
        signal_payload={"price": 2450.0, "qty": 2.5},
    )

    assert payload == {
        "instance_id": "ott_eth_5m",
        "symbol": "ETHUSDT",
        "side": "flat",
        "qty": 0.0,
        "entry_price": 0.0,
        "state_json": {},
    }


def test_fetch_current_side_filters_by_instance_id():
    from apps.executor_service.service import fetch_current_side

    cur = RecordingCursor(row=("long",))

    side = fetch_current_side(cur=cur, instance_id="ott_eth_5m")

    assert side == "long"
    query, params = cur.executed[0]
    assert "WHERE instance_id = %s" in query
    assert params == ("ott_eth_5m",)


def test_upsert_position_side_inserts_instance_id():
    from apps.executor_service.service import upsert_position_side

    cur = RecordingCursor()

    upsert_position_side(
        cur=cur,
        position_payload={
            "instance_id": "ott_eth_5m",
            "symbol": "ETHUSDT",
            "side": "long",
            "qty": 2.5,
            "entry_price": 2450.0,
            "state_json": {},
        },
    )

    query, params = cur.executed[0]
    assert "INSERT INTO position_state (instance_id, symbol, side, qty, entry_price, state_json)" in query
    assert params[0] == "ott_eth_5m"
