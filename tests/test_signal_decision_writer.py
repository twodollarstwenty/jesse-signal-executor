import json
import math

from apps.signal_service.writer import build_decision_hash


def test_decision_hash_is_deterministic():
    payload = dict(
        instance_id="ott_eth_5m",
        strategy="StandardGrid_LightMartingale_v1",
        symbol="ETHUSDT",
        timeframe="5m",
        candle_timestamp=1712188800000,
    )

    assert build_decision_hash(**payload) == build_decision_hash(**payload)


def test_decision_hash_changes_when_candle_timestamp_changes():
    base_payload = dict(
        instance_id="ott_eth_5m",
        strategy="StandardGrid_LightMartingale_v1",
        symbol="ETHUSDT",
        timeframe="5m",
    )

    assert build_decision_hash(candle_timestamp=1712188800000, **base_payload) != build_decision_hash(
        candle_timestamp=1712189100000,
        **base_payload,
    )


class FakeCursor:
    def __init__(self):
        self.calls = []

    def execute(self, sql, params):
        self.calls.append((sql, params))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_insert_signal_decision_writes_expected_row(monkeypatch):
    import apps.signal_service.writer as module

    conn = FakeConnection()
    monkeypatch.setattr(module, "connect", lambda: conn)

    module.insert_signal_decision(
        instance_id="ott_eth_5m",
        strategy="StandardGrid_LightMartingale_v1",
        symbol="ETHUSDT",
        timeframe="5m",
        signal_time="2026-04-30T12:55:00Z",
        candle_timestamp=1714481700000,
        intent="long",
        action="open_long",
        emitted=True,
        decision_status="emitted",
        reason_code="entry_signal_emitted",
        payload={"runtime": {"emitted": True}},
    )

    sql, params = conn.cursor_obj.calls[0]
    assert "INSERT INTO signal_decision_events" in sql
    assert params[0] == "ott_eth_5m"
    assert params[5] == 1714481700000
    assert params[9] is True
    assert params[10] == "emitted"
    assert params[11] == "entry_signal_emitted"
    assert json.loads(params[12]) == {"runtime": {"emitted": True}}
    assert conn.closed is True


def test_insert_signal_decision_normalizes_nan_values_before_json_encoding(monkeypatch):
    import apps.signal_service.writer as module

    conn = FakeConnection()
    monkeypatch.setattr(module, "connect", lambda: conn)

    module.insert_signal_decision(
        instance_id="ott_eth_5m",
        strategy="StandardGrid_LightMartingale_v1",
        symbol="ETHUSDT",
        timeframe="5m",
        signal_time="2026-04-30T12:55:00Z",
        candle_timestamp=1714481700000,
        intent="flat",
        action="none",
        emitted=False,
        decision_status="noop",
        reason_code="no_entry_level_hit",
        payload={"box": {"lower_bound": math.nan, "box_width_pct": math.inf}},
    )

    sql, params = conn.cursor_obj.calls[0]
    assert "INSERT INTO signal_decision_events" in sql
    assert json.loads(params[12]) == {"box": {"lower_bound": None, "box_width_pct": None}}


def test_insert_signal_decision_normalizes_float_like_nan_values(monkeypatch):
    import apps.signal_service.writer as module

    class FloatLikeNaN:
        def __float__(self):
            return math.nan

    conn = FakeConnection()
    monkeypatch.setattr(module, "connect", lambda: conn)

    module.insert_signal_decision(
        instance_id="ott_eth_5m",
        strategy="StandardGrid_LightMartingale_v1",
        symbol="ETHUSDT",
        timeframe="5m",
        signal_time="2026-04-30T12:55:00Z",
        candle_timestamp=1714481700000,
        intent="flat",
        action="none",
        emitted=False,
        decision_status="noop",
        reason_code="no_entry_level_hit",
        payload={"box": {"lower_bound": FloatLikeNaN()}},
    )

    _, params = conn.cursor_obj.calls[0]
    assert json.loads(params[12]) == {"box": {"lower_bound": None}}
