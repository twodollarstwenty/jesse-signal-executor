def test_parse_ticker_price_response_returns_float_price_and_symbol():
    from scripts.fetch_binance_market_snapshot import parse_ticker_price_response

    data = {"symbol": "ETHUSDT", "price": "2516.80"}

    snapshot = parse_ticker_price_response(data)

    assert snapshot == {
        "symbol": "ETHUSDT",
        "price": 2516.8,
    }
