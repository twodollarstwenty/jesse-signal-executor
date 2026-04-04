from apps.signal_service.writer import build_signal_hash


def test_signal_hash_is_deterministic():
    payload = dict(
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        timeframe="5m",
        signal_time="2026-04-04T00:00:00Z",
        action="open_long",
    )
    assert build_signal_hash(**payload) == build_signal_hash(**payload)
