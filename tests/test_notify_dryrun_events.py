def test_format_execution_event_message_contains_core_fields():
    from scripts.notify_dryrun_events import format_execution_event_message

    row = {
        "created_at": "2026-04-05T12:35:00+08:00",
        "strategy": "Ott2butKAMA_RiskManaged25",
        "symbol": "ETHUSDT",
        "action": "open_long",
        "decision": "execute",
        "reason": None,
    }

    text = format_execution_event_message(row)

    assert "[DRY-RUN]" in text
    assert "strategy: Ott2butKAMA_RiskManaged25" in text
    assert "action: open_long" in text
    assert "decision: execute" in text


def test_format_backtest_summary_message_contains_key_metrics():
    from apps.notifications.wecom import format_backtest_summary_message

    text = format_backtest_summary_message(
        baseline="Ott2butKAMA",
        candidate="Ott2butKAMA_RiskManaged25",
        symbol="ETHUSDT",
        timeframe="5m",
        window="2025-10-05 -> 2026-04-05",
        trades="93",
        win_rate="43.01%",
        net_profit="94.26%",
        max_drawdown="-20.12%",
    )

    assert "[BACKTEST]" in text
    assert "candidate: Ott2butKAMA_RiskManaged25" in text
    assert "net_profit: 94.26%" in text
