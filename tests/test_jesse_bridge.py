from unittest.mock import patch

from apps.signal_service.jesse_bridge.emitter import (
    build_signal_notification_message,
    candle_timestamp_to_iso,
    emit_signal,
)


def test_candle_timestamp_to_iso_formats_utc():
    value = candle_timestamp_to_iso(1712188800000)
    assert value.endswith("Z")


def test_build_signal_notification_message_formats_open_long_payload():
    message = build_signal_notification_message(
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        timeframe="5m",
        signal_time="2024-04-04T00:00:00Z",
        action="open_long",
        payload={"source": "jesse", "price": 2500.0, "position_side": "long"},
    )

    assert message == "\n".join(
        [
            "[交易信号]",
            "策略: Ott2butKAMA",
            "交易对: ETHUSDT",
            "周期: 5m",
            "动作: 开多",
            "信号时间: 2024-04-04T00:00:00Z",
            "价格: 2500.0",
            "仓位方向: long",
            "来源: jesse",
        ]
    )


def test_build_signal_notification_message_uses_na_for_none_payload_values():
    message = build_signal_notification_message(
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        timeframe="5m",
        signal_time="2024-04-04T00:00:00Z",
        action="close_short",
        payload={"source": None, "price": None},
    )

    assert message == "\n".join(
        [
            "[交易信号]",
            "策略: Ott2butKAMA",
            "交易对: ETHUSDT",
            "周期: 5m",
            "动作: 平空",
            "信号时间: 2024-04-04T00:00:00Z",
            "价格: N/A",
            "仓位方向: short",
            "来源: N/A",
        ]
    )


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
    mock_insert.assert_called_once_with(
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        timeframe="5m",
        signal_time="2024-04-04T00:00:00Z",
        action="open_long",
        payload={"source": "jesse"},
    )


@patch("apps.signal_service.jesse_bridge.emitter.send_text_message")
@patch("apps.signal_service.jesse_bridge.emitter.insert_signal")
def test_emit_signal_sends_notification_for_supported_action(mock_insert, mock_send):
    emit_signal(
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        timeframe="5m",
        candle_timestamp=1712188800000,
        action="open_long",
        payload={"source": "jesse", "price": 2500.0, "position_side": "long"},
    )

    mock_insert.assert_called_once()
    mock_send.assert_called_once_with(
        build_signal_notification_message(
            strategy="Ott2butKAMA",
            symbol="ETHUSDT",
            timeframe="5m",
            signal_time="2024-04-04T00:00:00Z",
            action="open_long",
            payload={"source": "jesse", "price": 2500.0, "position_side": "long"},
        )
    )


@patch("apps.signal_service.jesse_bridge.emitter.send_text_message")
@patch("apps.signal_service.jesse_bridge.emitter.insert_signal")
def test_emit_signal_sends_notification_for_close_action(mock_insert, mock_send):
    emit_signal(
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        timeframe="5m",
        candle_timestamp=1712188800000,
        action="close_short",
        payload={"source": "jesse", "price": 2490.5, "position_side": "short"},
    )

    mock_insert.assert_called_once()
    mock_send.assert_called_once_with(
        build_signal_notification_message(
            strategy="Ott2butKAMA",
            symbol="ETHUSDT",
            timeframe="5m",
            signal_time="2024-04-04T00:00:00Z",
            action="close_short",
            payload={"source": "jesse", "price": 2490.5, "position_side": "short"},
        )
    )


@patch("apps.signal_service.jesse_bridge.emitter.send_text_message")
@patch("apps.signal_service.jesse_bridge.emitter.insert_signal")
def test_emit_signal_skips_notification_for_unsupported_action(mock_insert, mock_send):
    emit_signal(
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        timeframe="5m",
        candle_timestamp=1712188800000,
        action="none",
        payload={"source": "jesse"},
    )

    mock_insert.assert_called_once()
    mock_send.assert_not_called()


@patch("apps.signal_service.jesse_bridge.emitter.send_text_message", side_effect=RuntimeError("boom"))
@patch("apps.signal_service.jesse_bridge.emitter.insert_signal")
def test_emit_signal_suppresses_notification_failure(mock_insert, _mock_send):
    emit_signal(
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        timeframe="5m",
        candle_timestamp=1712188800000,
        action="close_short",
        payload={"source": "jesse", "price": 2490.5},
    )

    mock_insert.assert_called_once()
