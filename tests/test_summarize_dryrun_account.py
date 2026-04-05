def test_compute_current_equity_from_realized_and_unrealized_pnl():
    from scripts.summarize_dryrun_account import compute_current_equity

    equity = compute_current_equity(initial_capital=1000.0, realized_pnl=35.2, unrealized_pnl=-4.8)

    assert equity == 1030.4


def test_compute_unrealized_pnl_for_long_position():
    from scripts.summarize_dryrun_account import compute_unrealized_pnl

    position = {"side": "long", "qty": 1.0, "entry_price": 2058.05}

    pnl = compute_unrealized_pnl(position=position, current_price=2057.99)

    assert pnl == -0.06


def test_render_account_summary_contains_core_fields():
    from scripts.summarize_dryrun_account import render_account_summary

    text = render_account_summary(
        initial_capital=1000.0,
        realized_pnl=35.2,
        unrealized_pnl=-4.8,
        current_equity=1030.4,
        position={"side": "long", "qty": 1.0, "entry_price": 2058.05},
        current_price=2057.99,
    )

    assert "初始资金: 1000.00" in text
    assert "已实现盈亏: +35.20" in text
    assert "未实现盈亏: -4.80" in text
    assert "当前权益: 1030.40" in text
    assert "当前持仓: long" in text
    assert "持仓数量: 1.0" in text
    assert "开仓价: 2058.05" in text
    assert "当前价: 2057.99" in text


def test_compute_realized_pnl_from_executed_signal_cycle_for_long_position():
    from scripts.summarize_dryrun_account import compute_realized_pnl_from_signals

    rows = [
        ("open_long", {"price": 2000.0, "qty": 1.0}),
        ("close_long", {"price": 2050.0, "qty": 1.0, "position_side": "long"}),
    ]

    pnl = compute_realized_pnl_from_signals(rows)

    assert pnl == 50.0


def test_compute_realized_pnl_from_executed_signal_cycle_for_short_position():
    from scripts.summarize_dryrun_account import compute_realized_pnl_from_signals

    rows = [
        ("open_short", {"price": 2100.0, "qty": 1.0}),
        ("close_short", {"price": 2060.0, "qty": 1.0, "position_side": "short"}),
    ]

    pnl = compute_realized_pnl_from_signals(rows)

    assert pnl == 40.0
