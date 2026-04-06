def test_translate_actions_to_chinese_direction_labels():
    from scripts.build_trade_history_panel import translate_action_label

    assert translate_action_label("open_long") == "开多"
    assert translate_action_label("open_short") == "开空"
    assert translate_action_label("close_long") == "平多"
    assert translate_action_label("close_short") == "平空"


def test_render_trade_history_row_contains_requested_fields():
    from scripts.build_trade_history_panel import render_trade_history_row

    row = {
        "time": "2026-04-06 09:23:25",
        "contract": "ETHUSDT 永续",
        "direction": "平空",
        "price": 2114.84,
        "price_text": "2114.84",
        "qty_text": "0.362 ETH",
        "fee_text": "--",
        "role": "dry-run",
        "realized_pnl_text": "+4.96060999 USDT",
    }

    text = render_trade_history_row(row)

    assert "2026-04-06 09:23:25" in text
    assert "ETHUSDT 永续" in text
    assert "平空" in text
    assert "2114.84" in text
    assert "0.362 ETH" in text
    assert "--" in text
    assert "dry-run" in text
    assert "+4.96060999 USDT" in text


def test_build_trade_row_uses_dryrun_placeholders_for_fee_and_role():
    from scripts.build_trade_history_panel import build_trade_row

    row = build_trade_row(
        signal_time="2026-04-06 09:23:25",
        symbol="ETHUSDT",
        action="close_short",
        payload={"price": 2114.84, "qty": 0.362},
        realized_pnl=4.96060999,
    )

    assert row["fee_text"] == "--"
    assert row["role"] == "dry-run"
    assert row["direction"] == "平空"


def test_compute_realized_pnl_pairs_open_and_close_long():
    from scripts.build_trade_history_panel import compute_realized_pnl_rows

    rows = [
        ("2026-04-06 09:20:00", "ETHUSDT", "open_long", {"price": 2000.0, "qty": 1.0}),
        ("2026-04-06 09:30:00", "ETHUSDT", "close_long", {"price": 2050.0, "qty": 1.0}),
    ]

    trade_rows = compute_realized_pnl_rows(rows)

    assert trade_rows[-1]["realized_pnl_text"] == "+50.00000000 USDT"


def test_build_trade_row_replaces_zero_price_with_placeholder():
    from scripts.build_trade_history_panel import build_trade_row

    row = build_trade_row(
        signal_time="2026-04-06 09:23:25",
        symbol="ETHUSDT",
        action="open_long",
        payload={"price": 0.0, "qty": 1.0},
        realized_pnl=0.0,
    )

    assert row["price_text"] == "--"
