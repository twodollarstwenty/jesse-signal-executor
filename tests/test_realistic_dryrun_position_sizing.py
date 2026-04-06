def test_compute_position_qty_from_initial_capital_leverage_and_fraction():
    from scripts.build_current_position_panel import compute_position_qty

    qty = compute_position_qty(
        initial_capital=1000.0,
        leverage=10.0,
        position_fraction=0.2,
        current_price=2100.0,
    )

    assert qty == 0.95238


def test_compute_position_qty_returns_zero_for_invalid_price():
    from scripts.build_current_position_panel import compute_position_qty

    assert compute_position_qty(
        initial_capital=1000.0,
        leverage=10.0,
        position_fraction=0.2,
        current_price=0.0,
    ) == 0.0


def test_compute_notional_usdt_uses_realistic_qty():
    from scripts.build_current_position_panel import compute_notional_usdt

    assert compute_notional_usdt(qty=0.95238, mark_price=2100.0) == 2000.0
