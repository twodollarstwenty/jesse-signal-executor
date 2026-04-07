def test_parse_klines_response_returns_close_prices_and_latest_timestamp():
    from scripts.fetch_binance_kline_snapshot import parse_klines_response

    payload = [
        [1712188800000, "2500.0", "2510.0", "2490.0", "2505.0", "100"],
        [1712189100000, "2505.0", "2520.0", "2500.0", "2516.8", "120"],
    ]

    snapshot = parse_klines_response(payload)

    assert snapshot["close_prices"] == [2505.0, 2516.8]
    assert snapshot["latest_timestamp"] == 1712189100000


def test_fetch_recent_klines_retries_once_before_failing(monkeypatch):
    from scripts.fetch_binance_kline_snapshot import fetch_recent_klines

    calls = {"count": 0}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'[[1712188800000, "2500.0", "2510.0", "2490.0", "2505.0", "100"], [1712189100000, "2505.0", "2520.0", "2500.0", "2516.8", "120"]]'

    def flaky_urlopen(url, timeout):
        calls["count"] += 1
        if calls["count"] == 1:
            raise TimeoutError("simulated timeout")
        return FakeResponse()

    monkeypatch.setattr("scripts.fetch_binance_kline_snapshot.urllib.request.urlopen", flaky_urlopen)

    snapshot = fetch_recent_klines(symbol="ETHUSDT", interval="5m", limit=2)

    assert snapshot["close_prices"] == [2505.0, 2516.8]
    assert snapshot["latest_timestamp"] == 1712189100000
    assert calls["count"] == 2
