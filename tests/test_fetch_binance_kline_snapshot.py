def test_parse_klines_response_returns_close_prices_and_latest_timestamp():
    from scripts.fetch_binance_kline_snapshot import parse_klines_response

    payload = [
        [1712188800000, "2500.0", "2510.0", "2490.0", "2505.0", "100"],
        [1712189100000, "2505.0", "2520.0", "2500.0", "2516.8", "120"],
    ]

    snapshot = parse_klines_response(payload)

    assert snapshot["close_prices"] == [2505.0, 2516.8]
    assert snapshot["latest_timestamp"] == 1712189100000
