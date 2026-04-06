import json
import urllib.request


def parse_klines_response(payload: list[list]) -> dict:
    return {
        "close_prices": [float(row[4]) for row in payload],
        "latest_timestamp": int(payload[-1][0]) if payload else 0,
    }


def fetch_recent_klines(*, symbol: str, interval: str = "5m", limit: int = 50) -> dict:
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    with urllib.request.urlopen(url, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    snapshot = parse_klines_response(payload)
    snapshot["symbol"] = symbol
    return snapshot
