def test_evaluate_direction_returns_long_when_cross_up_and_chop_filter_pass():
    from strategies.shared.ott2butkama_core import evaluate_direction

    result = evaluate_direction(
        cross_up=True,
        cross_down=False,
        chop_value=65.0,
        chop_upper_band=54.4,
        chop_lower_band=45.6,
    )

    assert result == "long"


def test_evaluate_direction_returns_short_when_cross_down_and_chop_filter_pass():
    from strategies.shared.ott2butkama_core import evaluate_direction

    result = evaluate_direction(
        cross_up=False,
        cross_down=True,
        chop_value=40.0,
        chop_upper_band=54.4,
        chop_lower_band=45.6,
    )

    assert result == "short"


def test_evaluate_direction_returns_flat_when_neither_condition_passes():
    from strategies.shared.ott2butkama_core import evaluate_direction

    result = evaluate_direction(
        cross_up=False,
        cross_down=False,
        chop_value=50.0,
        chop_upper_band=54.4,
        chop_lower_band=45.6,
    )

    assert result == "flat"
