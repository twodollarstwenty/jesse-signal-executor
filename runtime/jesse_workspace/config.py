config = {
    "app": {
        "considering_timeframes": ["5m"],
        "trading_mode": "backtest",
        "debug_mode": False,
    },
    "env": {
        "exchanges": {
            "Binance Perpetual Futures": {
                "fee": 0.0004,
                "balance": 10000,
                "type": "futures",
                "futures_leverage": 2,
            }
        }
    },
}
