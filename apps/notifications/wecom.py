import os


def notifications_enabled() -> bool:
    return os.getenv("NOTIFY_ENABLED", "0") == "1"


def build_text_payload(content: str) -> dict:
    return {
        "msgtype": "text",
        "text": {"content": content},
    }


def send_text_message(content: str) -> bool:
    webhook = os.getenv("WECOM_BOT_WEBHOOK")
    if not notifications_enabled() or not webhook:
        return False

    try:
        import requests

        response = requests.post(webhook, json=build_text_payload(content), timeout=5)
        response.raise_for_status()
    except Exception:
        return False

    return True


def format_backtest_summary_message(
    *,
    baseline: str,
    candidate: str,
    symbol: str,
    timeframe: str,
    window: str,
    trades: str,
    win_rate: str,
    net_profit: str,
    max_drawdown: str,
) -> str:
    return "\n".join(
        [
            "[BACKTEST]",
            f"baseline: {baseline}",
            f"candidate: {candidate}",
            f"symbol: {symbol}",
            f"timeframe: {timeframe}",
            f"window: {window}",
            f"trades: {trades}",
            f"win_rate: {win_rate}",
            f"net_profit: {net_profit}",
            f"max_drawdown: {max_drawdown}",
        ]
    )
