import logging
from datetime import datetime, timezone

from apps.notifications.wecom import send_text_message
from apps.signal_service.writer import insert_signal


logger = logging.getLogger(__name__)


NOTIFIABLE_ACTION_LABELS = {
    "open_long": "开多",
    "open_short": "开空",
    "close_long": "平多",
    "close_short": "平空",
}


def candle_timestamp_to_iso(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def infer_position_side(action: str) -> str:
    if action in {"open_long", "close_long"}:
        return "long"
    if action in {"open_short", "close_short"}:
        return "short"
    return "N/A"


def build_signal_notification_message(
    *, strategy: str, symbol: str, timeframe: str, signal_time: str, action: str, payload: dict
) -> str:
    action_label = NOTIFIABLE_ACTION_LABELS.get(action)
    if action_label is None:
        raise ValueError(f"unsupported notification action: {action}")

    price = payload.get("price")
    source = payload.get("source")

    return "\n".join(
        [
            "[交易信号]",
            f"策略: {strategy}",
            f"交易对: {symbol}",
            f"周期: {timeframe}",
            f"动作: {action_label}",
            f"信号时间: {signal_time}",
            f"价格: {price if price is not None else 'N/A'}",
            f"仓位方向: {payload.get('position_side') or infer_position_side(action)}",
            f"来源: {source if source is not None else 'N/A'}",
        ]
    )


def notify_signal_if_supported(
    *, strategy: str, symbol: str, timeframe: str, signal_time: str, action: str, payload: dict
) -> None:
    if action not in NOTIFIABLE_ACTION_LABELS:
        return

    try:
        send_text_message(
            build_signal_notification_message(
                strategy=strategy,
                symbol=symbol,
                timeframe=timeframe,
                signal_time=signal_time,
                action=action,
                payload=payload,
            )
        )
    except Exception:
        logger.exception("Failed to send WeCom notification for signal action=%s symbol=%s", action, symbol)


def emit_signal(
    *, instance_id: str, strategy: str, symbol: str, timeframe: str, candle_timestamp: int, action: str, payload: dict
) -> None:
    signal_time = candle_timestamp_to_iso(candle_timestamp)

    insert_signal(
        instance_id=instance_id,
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        signal_time=signal_time,
        action=action,
        payload=payload,
    )

    notify_signal_if_supported(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        signal_time=signal_time,
        action=action,
        payload=payload,
    )
