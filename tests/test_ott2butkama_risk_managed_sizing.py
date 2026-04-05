def test_compute_risk_fraction_from_hyperparameter():
    from strategies.jesse.Ott2butKAMA_RiskManaged import Ott2butKAMA_RiskManaged

    strategy = object.__new__(Ott2butKAMA_RiskManaged)
    strategy.hp = {"risk_per_trade": 10}

    assert strategy.risk_fraction == 0.01


def test_compute_risk_based_qty_for_long_uses_stop_distance():
    from strategies.jesse.Ott2butKAMA_RiskManaged import Ott2butKAMA_RiskManaged

    strategy = object.__new__(Ott2butKAMA_RiskManaged)
    strategy.balance = 10000
    strategy.price = 2000
    strategy.hp = {"risk_per_trade": 10}

    qty = strategy.compute_risk_based_qty(stop_price=1980)

    assert qty == 5.0


def test_compute_risk_based_qty_returns_zero_for_invalid_stop_distance():
    from strategies.jesse.Ott2butKAMA_RiskManaged import Ott2butKAMA_RiskManaged

    strategy = object.__new__(Ott2butKAMA_RiskManaged)
    strategy.balance = 10000
    strategy.price = 2000
    strategy.hp = {"risk_per_trade": 10}

    assert strategy.compute_risk_based_qty(stop_price=2000) == 0
    assert strategy.compute_risk_based_qty(stop_price=2001) == 0


def test_compute_risk_based_qty_for_short_uses_stop_above_price():
    from strategies.jesse.Ott2butKAMA_RiskManaged import Ott2butKAMA_RiskManaged

    strategy = object.__new__(Ott2butKAMA_RiskManaged)
    strategy.balance = 10000
    strategy.price = 2000
    strategy.hp = {"risk_per_trade": 10}

    qty = strategy.compute_risk_based_qty(stop_price=2020, side="short")

    assert qty == 5.0
