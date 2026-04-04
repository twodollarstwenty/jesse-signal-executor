from unittest.mock import patch

from apps.signal_service.jesse_bridge.emitter import candle_timestamp_to_iso, emit_signal


def test_candle_timestamp_to_iso_formats_utc():
    value = candle_timestamp_to_iso(1712188800000)
    assert value.endswith("Z")


@patch("apps.signal_service.jesse_bridge.emitter.insert_signal")
def test_emit_signal_calls_insert_signal(mock_insert):
    emit_signal(
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        timeframe="5m",
        candle_timestamp=1712188800000,
        action="open_long",
        payload={"source": "jesse"},
    )
    assert mock_insert.called
