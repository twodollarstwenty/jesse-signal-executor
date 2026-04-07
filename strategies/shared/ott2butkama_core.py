def evaluate_direction(*, cross_up: bool, cross_down: bool, chop_value: float, chop_upper_band: float, chop_lower_band: float) -> str:
    if cross_up and chop_value > chop_upper_band:
        return "long"
    if cross_down and chop_value < chop_lower_band:
        return "short"
    return "flat"
