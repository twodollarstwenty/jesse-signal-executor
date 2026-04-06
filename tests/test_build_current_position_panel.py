def test_compute_notional_usdt_from_qty_and_mark_price():
    from scripts.build_current_position_panel import compute_notional_usdt

    assert compute_notional_usdt(qty=1.0, mark_price=2075.55) == 2075.55


def test_compute_margin_estimate_from_notional_and_leverage():
    from scripts.build_current_position_panel import compute_margin_estimate

    assert compute_margin_estimate(notional_usdt=2075.55, leverage=10) == 207.56


def test_compute_margin_ratio_estimate_from_margin_and_equity():
    from scripts.build_current_position_panel import compute_margin_ratio_estimate

    assert compute_margin_ratio_estimate(margin=207.56, equity=1000.0) == 20.76


def test_render_position_panel_contains_requested_fields():
    from scripts.build_current_position_panel import render_position_panel

    panel = {
        "symbol": "ETHUSDT 永续",
        "qty": 1.0,
        "notional_usdt": 2075.55,
        "margin": 207.56,
        "margin_ratio": 20.76,
        "entry_price": 2058.05,
        "mark_price": 2075.55,
        "liquidation_price": "--",
        "pnl_text": "+17.50 USDT (+0.85%)",
        "tp_sl": "TP 2120 / SL 2041",
    }

    text = render_position_panel(panel)

    assert "符号: ETHUSDT 永续" in text
    assert "大小(ETH): 1.0" in text
    assert "名义金额(USDT): 2075.55" in text
    assert "保证金: 207.56" in text
    assert "保证金比率: 20.76%" in text
    assert "开仓价格: 2058.05" in text
    assert "标记价格: 2075.55" in text
    assert "强平价格: --" in text
    assert "收益额（收益率）: +17.50 USDT (+0.85%)" in text
    assert "止盈/止损: TP 2120 / SL 2041" in text
