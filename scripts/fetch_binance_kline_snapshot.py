import json
import urllib.request


def parse_klines_response(payload: list[list]) -> dict:
    return {
        "close_prices": [float(row[4]) for row in payload],
        "latest_timestamp": int(payload[-1][0]) if payload else 0,
        "candles": [
            [int(row[0]), float(row[1]), float(row[4]), float(row[2]), float(row[3]), float(row[5])]
            for row in payload
        ],
    }


def fetch_recent_klines(*, symbol: str, interval: str = "5m", limit: int = 50) -> dict:
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    last_error = None
    for _ in range(2):
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except Exception as exc:
            last_error = exc
    else:
        raise last_error
    snapshot = parse_klines_response(payload)
    snapshot["symbol"] = symbol
    return snapshot
