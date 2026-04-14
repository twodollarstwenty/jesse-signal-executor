from apps.signal_service.writer import build_signal_hash


def test_signal_hash_is_deterministic():
    payload = dict(
        instance_id="ott_eth_5m",
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        timeframe="5m",
        signal_time="2026-04-04T00:00:00Z",
        action="open_long",
    )
    assert build_signal_hash(**payload) == build_signal_hash(**payload)


def test_signal_hash_changes_when_instance_id_changes():
    base_payload = dict(
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        timeframe="5m",
        signal_time="2026-04-04T00:00:00Z",
        action="open_long",
    )

    assert build_signal_hash(instance_id="ott_eth_5m", **base_payload) != build_signal_hash(
        instance_id="ott_btc_5m", **base_payload
    )
