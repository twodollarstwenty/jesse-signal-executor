def test_layer_sizes_sum_to_total_position_budget():
    from strategies.jesse.Ott2butKAMA_RiskManaged25_Grid import compute_layer_sizes

    layers = compute_layer_sizes(total_qty=10.0)

    assert layers == [4.0, 3.0, 3.0]


def test_long_layer_trigger_prices_step_down_from_base_entry():
    from strategies.jesse.Ott2butKAMA_RiskManaged25_Grid import compute_long_layer_prices

    prices = compute_long_layer_prices(entry_price=100.0)

    assert prices == [100.0, 99.6, 99.2]


def test_short_layer_trigger_prices_step_up_from_base_entry():
    from strategies.jesse.Ott2butKAMA_RiskManaged25_Grid import compute_short_layer_prices

    prices = compute_short_layer_prices(entry_price=100.0)

    assert prices == [100.0, 100.4, 100.8]
