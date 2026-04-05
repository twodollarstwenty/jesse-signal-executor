import os
import json
import urllib.request


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
        try:
            import requests

            response = requests.post(webhook, json=build_text_payload(content), timeout=5)
            response.raise_for_status()
        except ModuleNotFoundError:
            payload = json.dumps(build_text_payload(content)).encode("utf-8")
            request = urllib.request.Request(
                webhook,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                if getattr(response, "status", 200) >= 400:
                    return False
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
            "[回测结果]",
            f"基线策略: {baseline}",
            f"候选策略: {candidate}",
            f"交易对: {symbol}",
            f"周期: {timeframe}",
            f"区间: {window}",
            f"交易次数: {trades}",
            f"胜率: {win_rate}",
            f"净收益: {net_profit}",
            f"最大回撤: {max_drawdown}",
        ]
    )
