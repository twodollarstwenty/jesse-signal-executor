import talib

import custom_indicators_ottkama as cta


def build_feature_state(*, closes, ott_len: int, ott_percent: float, chop_rsi_len: int, chop_bandwidth: int) -> dict:
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
