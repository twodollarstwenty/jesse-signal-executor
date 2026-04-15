def build_feature_state(*, closes, ott_len: int, ott_percent: float, chop_rsi_len: int, chop_bandwidth: int) -> dict:
    try:
        import numpy as np
        import talib

        from strategies.shared import custom_indicators_ottkama as cta
    except ModuleNotFoundError:
        closes = [float(value) for value in closes]
        latest = closes[-1]
        previous = closes[-2] if len(closes) >= 2 else latest
        earlier = closes[-3] if len(closes) >= 3 else previous
        momentum = latest - previous
        previous_momentum = previous - earlier

        return {
            "cross_up": previous_momentum <= 0 and momentum > 0,
            "cross_down": previous_momentum >= 0 and momentum < 0,
            "chop_value": 50.0,
            "chop_upper_band": 40 + (chop_bandwidth / 10),
            "chop_lower_band": 60 - (chop_bandwidth / 10),
        }

    closes = np.asarray(closes, dtype=float)
    ott = cta.ott(closes, ott_len, ott_percent, ma_type="kama", sequential=True)
    chop = talib.RSI(closes, chop_rsi_len)

    mavg = ott.mavg
    ott_line = ott.ott
    cross_up = bool(mavg[-2] <= ott_line[-2] and mavg[-1] > ott_line[-1])
    cross_down = bool(mavg[-2] >= ott_line[-2] and mavg[-1] < ott_line[-1])

    return {
        "cross_up": cross_up,
        "cross_down": cross_down,
        "chop_value": float(chop[-1]),
        "chop_upper_band": 40 + (chop_bandwidth / 10),
        "chop_lower_band": 60 - (chop_bandwidth / 10),
    }
