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


def test_fetch_current_position_filters_by_instance_id(monkeypatch):
    from scripts import summarize_dryrun_account as module

    calls: list[tuple[str, tuple]] = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params):
            calls.append((query, params))

        def fetchone(self):
            return ("long", 1.0, 2000.0)

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return FakeCursor()

        def close(self):
            pass

    monkeypatch.setattr(module, "connect", lambda: FakeConnection())

    position = module.fetch_current_position(symbol="ETHUSDT", instance_id="ott_eth_5m")

    assert position == {"side": "long", "qty": 1.0, "entry_price": 2000.0}
    assert "WHERE instance_id = %s AND symbol = %s" in calls[0][0]
    assert calls[0][1] == ("ott_eth_5m", "ETHUSDT")


def test_compute_realized_pnl_filters_by_instance_id(monkeypatch):
    from scripts import summarize_dryrun_account as module

    calls: list[tuple[str, tuple | None]] = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params=None):
            calls.append((query, params))

        def fetchall(self):
            return [
                ("open_long", {"price": 2000.0, "qty": 1.0}),
                ("close_long", {"price": 2050.0, "qty": 1.0, "position_side": "long"}),
            ]

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return FakeCursor()

        def close(self):
            pass

    monkeypatch.setattr(module, "connect", lambda: FakeConnection())

    pnl = module.compute_realized_pnl(instance_id="ott_eth_5m")

    assert pnl == 50.0
    assert "WHERE status = 'execute' AND instance_id = %s" in calls[0][0]
    assert calls[0][1] == ("ott_eth_5m",)
