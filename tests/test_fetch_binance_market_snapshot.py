def test_parse_ticker_price_response_returns_float_price_and_symbol():
    from scripts.fetch_binance_market_snapshot import parse_ticker_price_response

    data = {"symbol": "ETHUSDT", "price": "2516.80"}

    snapshot = parse_ticker_price_response(data)

    assert snapshot == {
        "symbol": "ETHUSDT",
        "price": 2516.8,
    }


def test_fetch_ticker_price_uses_binance_futures_endpoint(monkeypatch):
    from scripts.fetch_binance_market_snapshot import fetch_ticker_price

    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"symbol":"ETHUSDT","price":"2516.80"}'

    def fake_urlopen(url, timeout):
        captured["url"] = url
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("scripts.fetch_binance_market_snapshot.urllib.request.urlopen", fake_urlopen)

    snapshot = fetch_ticker_price(symbol="ETHUSDT")

    assert snapshot == {"symbol": "ETHUSDT", "price": 2516.8}
    assert captured["url"] == "https://fapi.binance.com/fapi/v1/ticker/price?symbol=ETHUSDT"
    assert captured["timeout"] == 5
