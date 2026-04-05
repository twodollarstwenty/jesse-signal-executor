import json
import urllib.request


def parse_ticker_price_response(data: dict) -> dict:
    return {
        "symbol": data["symbol"],
        "price": float(data["price"]),
    }


def fetch_ticker_price(*, symbol: str) -> dict:
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    with urllib.request.urlopen(url, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return parse_ticker_price_response(payload)
