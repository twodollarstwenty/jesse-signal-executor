from pathlib import Path
import sys

import pytest


def test_build_workspace_path_points_to_runtime_workspace():
    from scripts.run_jesse_live_loop import build_workspace_path

    workspace = build_workspace_path()

    assert workspace.name == "jesse_workspace"
    assert workspace.parent.name == "runtime"


def test_ensure_runtime_ready_raises_when_workspace_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import scripts.run_jesse_live_loop as module

    missing_workspace = tmp_path / "runtime" / "jesse_workspace"
    monkeypatch.setattr(module, "build_workspace_path", lambda: missing_workspace)

    with pytest.raises(FileNotFoundError, match="runtime/jesse_workspace"):
        module.ensure_runtime_ready()


def test_run_cycle_executes_strategy_step_without_resyncing_each_iteration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import scripts.run_jesse_live_loop as module

    calls: list[str] = []
    workspace = tmp_path / "runtime" / "jesse_workspace"
    workspace.mkdir(parents=True)

    monkeypatch.setattr(module, "ensure_runtime_ready", lambda: workspace)
    monkeypatch.setattr(
        module,
        "fetch_recent_klines",
        lambda symbol, interval="5m", limit=50: {
            "symbol": symbol,
            "close_prices": [2505.0, 2516.8, 2524.1],
            "latest_timestamp": 1712189100000,
        },
    )
    monkeypatch.setattr(module, "emit_strategy_signals", lambda loop_state=None: calls.append(f"emit:{Path.cwd()}"))
    module.LAST_PROCESSED_CANDLE_TS = 1712188800000

    original_cwd = Path.cwd()

    module.run_cycle()

    assert calls == [f"emit:{workspace}"]
    assert Path.cwd() == original_cwd


def test_run_cycle_skips_action_when_latest_candle_is_already_processed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    import scripts.run_jesse_live_loop as module

    workspace = tmp_path / "runtime" / "jesse_workspace"
    workspace.mkdir(parents=True)

    snapshot = {
        "symbol": "ETHUSDT",
        "close_prices": [2505.0, 2516.8, 2524.1],
        "latest_timestamp": 1712189100000,
        "timestamp": "2026-04-05T21:33:20+08:00",
    }

    monkeypatch.setattr(module, "ensure_runtime_ready", lambda: workspace)
    monkeypatch.setattr(module, "prepare_import_path", lambda current: None)
    monkeypatch.setattr(module, "fetch_recent_klines", lambda symbol, interval="5m", limit=50: snapshot)
    monkeypatch.setattr(
        module,
        "emit_strategy_signals",
        lambda loop_state=None: (_ for _ in ()).throw(AssertionError("should not emit for the same candle twice")),
    )
    module.LAST_PROCESSED_CANDLE_TS = 1712189100000

    module.run_cycle()

    output = capsys.readouterr().out.strip()
    assert "等待新 5m K 线" in output


def test_run_cycle_evaluates_once_when_new_candle_arrives(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import scripts.run_jesse_live_loop as module

    workspace = tmp_path / "runtime" / "jesse_workspace"
    workspace.mkdir(parents=True)

    snapshot = {
        "symbol": "ETHUSDT",
        "close_prices": [2505.0, 2516.8, 2524.1],
        "latest_timestamp": 1712189100000,
        "timestamp": "2026-04-05T21:33:20+08:00",
    }

    calls = []
    state_file = tmp_path / "last_candle_ts.txt"
    monkeypatch.setattr(module, "ensure_runtime_ready", lambda: workspace)
    monkeypatch.setattr(module, "prepare_import_path", lambda current: None)
    monkeypatch.setattr(module, "fetch_recent_klines", lambda symbol, interval="5m", limit=50: snapshot)
    monkeypatch.setattr(
        module,
        "emit_strategy_signals",
        lambda loop_state=None: calls.append(loop_state) or {**loop_state, "emitted": True},
    )
    module.LAST_PROCESSED_CANDLE_TS = 1712188800000
    monkeypatch.setenv("JESSE_LAST_CANDLE_FILE", str(state_file))

    module.run_cycle()

    assert len(calls) == 1
    assert module.LAST_PROCESSED_CANDLE_TS == 1712189100000


def test_run_cycle_initializes_baseline_candle_without_emitting_on_first_observation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys):
    import scripts.run_jesse_live_loop as module

    workspace = tmp_path / "runtime" / "jesse_workspace"
    workspace.mkdir(parents=True)

    snapshot = {
        "symbol": "ETHUSDT",
        "close_prices": [2505.0, 2516.8, 2524.1],
        "latest_timestamp": 1712189100000,
        "timestamp": "2026-04-05T21:33:20+08:00",
    }

    monkeypatch.setattr(module, "ensure_runtime_ready", lambda: workspace)
    monkeypatch.setattr(module, "prepare_import_path", lambda current: None)
    monkeypatch.setattr(module, "fetch_recent_klines", lambda symbol, interval="5m", limit=50: snapshot)
    monkeypatch.setattr(module, "emit_strategy_signals", lambda loop_state=None: (_ for _ in ()).throw(AssertionError("should not emit on first observation")))
    module.LAST_PROCESSED_CANDLE_TS = None
    state_file = tmp_path / "last_candle_ts.txt"
    monkeypatch.setenv("JESSE_LAST_CANDLE_FILE", str(state_file))

    module.run_cycle()

    output = capsys.readouterr().out.strip()
    assert "初始化 5m 基线K线，不发单" in output
    assert module.LAST_PROCESSED_CANDLE_TS == 1712189100000
    assert state_file.read_text().strip() == "1712189100000"


def test_run_cycle_reads_last_processed_candle_from_state_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys):
    import scripts.run_jesse_live_loop as module

    workspace = tmp_path / "runtime" / "jesse_workspace"
    workspace.mkdir(parents=True)

    snapshot = {
        "symbol": "ETHUSDT",
        "close_prices": [2505.0, 2516.8, 2524.1],
        "latest_timestamp": 1712189100000,
        "timestamp": "2026-04-05T21:33:20+08:00",
    }
    state_file = tmp_path / "last_candle_ts.txt"
    state_file.write_text("1712189100000")

    monkeypatch.setattr(module, "ensure_runtime_ready", lambda: workspace)
    monkeypatch.setattr(module, "prepare_import_path", lambda current: None)
    monkeypatch.setattr(module, "fetch_recent_klines", lambda symbol, interval="5m", limit=50: snapshot)
    monkeypatch.setattr(module, "emit_strategy_signals", lambda loop_state=None: (_ for _ in ()).throw(AssertionError("should not emit for already-processed candle")))
    module.LAST_PROCESSED_CANDLE_TS = None
    monkeypatch.setenv("JESSE_LAST_CANDLE_FILE", str(state_file))

    module.run_cycle()

    output = capsys.readouterr().out.strip()
    assert "等待新 5m K 线" in output


def test_prepare_import_path_prioritizes_runtime_workspace_without_changing_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import scripts.run_jesse_live_loop as module

    workspace = tmp_path / "runtime" / "jesse_workspace"
    strategies_dir = workspace / "strategies"
    strategies_dir.mkdir(parents=True)
    repo_strategies = tmp_path / "strategies" / "jesse"
    repo_strategies.mkdir(parents=True)

    original_cwd = Path.cwd()
    original_sys_path = sys.path.copy()
    monkeypatch.setattr(module, "ROOT", tmp_path)

    module.prepare_import_path(workspace)

    assert Path.cwd() == original_cwd
    assert sys.path[0] == str(workspace)
    assert sys.path[1] == str(strategies_dir)
    assert sys.path.index(str(workspace)) < sys.path.index(str(tmp_path))
    assert sys.path.index(str(strategies_dir)) < sys.path.index(str(repo_strategies))

    sys.path[:] = original_sys_path


def test_emit_strategy_signals_calls_strategy_entrypoints(monkeypatch: pytest.MonkeyPatch):
    import scripts.run_jesse_live_loop as module

    strategy = type("FakeStrategy", (), {})()
    strategy.symbol = "ETH-USDT"
    strategy.timeframe = "5m"
    strategy.buy = None
    strategy.sell = None

    calls: list[str] = []
    loop_state = {
        "timestamp": "2026-04-05T21:33:20+08:00",
        "price": 2516.8,
        "candle_timestamp": 1712188800000,
        "bias": "long",
        "position": {"side": "long", "qty": 1.0, "entry_price": 2506.8},
        "action": "open_long",
        "last_action": "open_long",
    }

    def fake_new_strategy():
        return strategy

    monkeypatch.setattr(module, "build_strategy_instance", fake_new_strategy)
    monkeypatch.setattr(module, "configure_strategy_for_signal_cycle", lambda current: calls.append("configure"))
    monkeypatch.setattr(module, "drive_strategy_cycle", lambda current, loop_state: calls.append("drive"))
    monkeypatch.setattr(module, "read_last_emitted_action", lambda: None)
    monkeypatch.setattr(module, "write_last_emitted_action", lambda action: None)
    module.LAST_EMITTED_ACTION = None

    module.emit_strategy_signals(loop_state)

    assert calls == ["configure", "drive"]


def test_emit_strategy_signals_suppresses_repeated_identical_action(monkeypatch: pytest.MonkeyPatch):
    import scripts.run_jesse_live_loop as module

    strategy = type("FakeStrategy", (), {})()
    strategy.symbol = "ETH-USDT"
    strategy.timeframe = "5m"
    strategy.buy = None
    strategy.sell = None

    loop_state = {
        "timestamp": "2026-04-05T21:33:20+08:00",
        "price": 2516.8,
        "candle_timestamp": 1712188800000,
        "bias": "long",
        "position": {"side": "long", "qty": 1.0, "entry_price": 2506.8},
        "action": "open_long",
        "last_action": "open_long",
    }

    monkeypatch.setattr(module, "build_strategy_instance", lambda: strategy)
    monkeypatch.setattr(module, "configure_strategy_for_signal_cycle", lambda current, loop_state=None: None)
    monkeypatch.setattr(module, "drive_strategy_cycle", lambda current, loop_state: True)
    monkeypatch.setattr(module, "read_last_emitted_action", lambda: "open_long")
    monkeypatch.setattr(module, "write_last_emitted_action", lambda action: None)
    module.LAST_EMITTED_ACTION = "open_long"

    result = module.emit_strategy_signals(loop_state)

    assert result["emitted"] is False


def test_emit_strategy_signals_emits_when_action_changes(monkeypatch: pytest.MonkeyPatch):
    import scripts.run_jesse_live_loop as module

    strategy = type("FakeStrategy", (), {})()
    strategy.symbol = "ETH-USDT"
    strategy.timeframe = "5m"
    strategy.buy = None
    strategy.sell = None

    loop_state = {
        "timestamp": "2026-04-05T21:33:20+08:00",
        "price": 2516.8,
        "candle_timestamp": 1712188800000,
        "bias": "short",
        "position": {"side": "short", "qty": 1.0, "entry_price": 2526.8},
        "action": "close_short",
        "last_action": "close_short",
    }

    monkeypatch.setattr(module, "build_strategy_instance", lambda: strategy)
    monkeypatch.setattr(module, "configure_strategy_for_signal_cycle", lambda current, loop_state=None: None)
    monkeypatch.setattr(module, "drive_strategy_cycle", lambda current, loop_state: True)
    monkeypatch.setattr(module, "read_last_emitted_action", lambda: None)
    monkeypatch.setattr(module, "write_last_emitted_action", lambda action: None)
    module.LAST_EMITTED_ACTION = "open_short"

    result = module.emit_strategy_signals(loop_state)

    assert result["emitted"] is True


def test_emit_strategy_signals_suppresses_repeated_action_across_process_boundary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import scripts.run_jesse_live_loop as module

    strategy = type("FakeStrategy", (), {})()
    strategy.symbol = "ETH-USDT"
    strategy.timeframe = "5m"
    strategy.buy = None
    strategy.sell = None

    loop_state = {
        "timestamp": "2026-04-05T21:33:20+08:00",
        "price": 2516.8,
        "candle_timestamp": 1712188800000,
        "bias": "long",
        "position": {"side": "long", "qty": 1.0, "entry_price": 2506.8},
        "action": "open_long",
        "last_action": "open_long",
    }

    state_file = tmp_path / "last_action.txt"
    state_file.write_text("open_long")
    monkeypatch.setenv("JESSE_LAST_ACTION_FILE", str(state_file))
    monkeypatch.setattr(module, "build_strategy_instance", lambda: strategy)
    monkeypatch.setattr(module, "configure_strategy_for_signal_cycle", lambda current, loop_state=None: None)
    monkeypatch.setattr(module, "drive_strategy_cycle", lambda current, loop_state: True)
    module.LAST_EMITTED_ACTION = None

    result = module.emit_strategy_signals(loop_state)

    assert result["emitted"] is False


def test_emit_strategy_signals_persists_new_action_for_next_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import scripts.run_jesse_live_loop as module

    strategy = type("FakeStrategy", (), {})()
    strategy.symbol = "ETH-USDT"
    strategy.timeframe = "5m"
    strategy.buy = None
    strategy.sell = None

    loop_state = {
        "timestamp": "2026-04-05T21:33:20+08:00",
        "price": 2516.8,
        "candle_timestamp": 1712188800000,
        "bias": "short",
        "position": {"side": "short", "qty": 1.0, "entry_price": 2526.8},
        "action": "close_short",
        "last_action": "close_short",
    }

    state_file = tmp_path / "last_action.txt"
    monkeypatch.setenv("JESSE_LAST_ACTION_FILE", str(state_file))
    monkeypatch.setattr(module, "build_strategy_instance", lambda: strategy)
    monkeypatch.setattr(module, "configure_strategy_for_signal_cycle", lambda current, loop_state=None: None)
    monkeypatch.setattr(module, "drive_strategy_cycle", lambda current, loop_state: True)
    module.LAST_EMITTED_ACTION = None

    result = module.emit_strategy_signals(loop_state)

    assert result["emitted"] is True
    assert state_file.read_text().strip() == "close_short"


def test_configure_strategy_for_signal_cycle_sets_instance_state_only():
    import scripts.run_jesse_live_loop as module

    class FakeStrategy:
        pass

    strategy = FakeStrategy()

    module.configure_strategy_for_signal_cycle(strategy)

    assert strategy.symbol == "ETH-USDT"
    assert strategy.exchange == "Binance Perpetual Futures"
    assert strategy.timeframe == "5m"
    assert strategy.buy is None
    assert strategy.sell is None
    assert strategy.pos_size == 1.0
    assert strategy.current_candle == [1712188800000, 2500.0, 2500.0, 2510.0, 2490.0, 100.0]
    assert strategy.price == 2500.0
    assert strategy.cross_down is True
    assert strategy.cross_up is False
    assert strategy.is_long is True
    assert strategy.is_short is False
    assert "pos_size" not in FakeStrategy.__dict__


def test_build_strategy_instance_imports_from_runtime_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import scripts.run_jesse_live_loop as module

    workspace = tmp_path / "runtime" / "jesse_workspace"
    runtime_package = workspace / "strategies" / "Ott2butKAMA"
    source_package = tmp_path / "strategies" / "jesse" / "Ott2butKAMA"
    runtime_package.mkdir(parents=True)
    source_package.mkdir(parents=True)
    (runtime_package / "__init__.py").write_text(
        "class Ott2butKAMA:\n    source = 'runtime'\n"
    )
    (source_package / "__init__.py").write_text(
        "class Ott2butKAMA:\n    source = 'source-tree'\n"
    )

    original_sys_path = sys.path.copy()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    module.prepare_import_path(workspace)

    for name in [
        "Ott2butKAMA",
    ]:
        sys.modules.pop(name, None)

    strategy = module.build_strategy_instance()

    assert strategy.__class__.source == "runtime"

    sys.path[:] = original_sys_path


def test_configure_strategy_for_signal_cycle_supports_read_only_property_classes():
    import scripts.run_jesse_live_loop as module

    class FakeStrategy:
        @property
        def pos_size(self):
            return 9.0

        @property
        def current_candle(self):
            return [0]

        @property
        def price(self):
            return 9.0

        @property
        def cross_down(self):
            return False

        @property
        def cross_up(self):
            return True

        @property
        def is_long(self):
            return False

        @property
        def is_short(self):
            return True

    strategy = FakeStrategy()

    module.configure_strategy_for_signal_cycle(strategy)

    assert strategy.pos_size == 1.0
    assert strategy.current_candle == [1712188800000, 2500.0, 2500.0, 2510.0, 2490.0, 100.0]
    assert strategy.price == 2500.0
    assert strategy.cross_down is True
    assert strategy.cross_up is False
    assert strategy.is_long is True
    assert strategy.is_short is False


def test_drive_strategy_cycle_works_when_runtime_properties_touch_exchange(monkeypatch: pytest.MonkeyPatch):
    import scripts.run_jesse_live_loop as module

    class FakeStrategy:
        pass

    strategy = FakeStrategy()

    module.configure_strategy_for_signal_cycle(strategy)

    assert strategy.exchange == "Binance Perpetual Futures"


def test_configure_strategy_for_signal_cycle_does_not_eagerly_call_original_property_getters():
    import scripts.run_jesse_live_loop as module

    class FakeStrategy:
        @property
        def pos_size(self):
            raise AssertionError("original getter should not run")

        @property
        def current_candle(self):
            raise AssertionError("original getter should not run")

        @property
        def price(self):
            raise AssertionError("original getter should not run")

        @property
        def cross_down(self):
            raise AssertionError("original getter should not run")

        @property
        def cross_up(self):
            raise AssertionError("original getter should not run")

        @property
        def is_long(self):
            raise AssertionError("original getter should not run")

        @property
        def is_short(self):
            raise AssertionError("original getter should not run")

    strategy = FakeStrategy()

    module.configure_strategy_for_signal_cycle(strategy)

    assert strategy.pos_size == 1.0
    assert strategy.current_candle == [1712188800000, 2500.0, 2500.0, 2510.0, 2490.0, 100.0]
    assert strategy.price == 2500.0
    assert strategy.cross_down is True
    assert strategy.cross_up is False
    assert strategy.is_long is True
    assert strategy.is_short is False


def test_render_flat_summary_contains_price_bias_action_and_emitted_flag():
    from scripts.run_jesse_live_loop import render_flat_summary

    text = render_flat_summary(
        timestamp="2026-04-05T21:03:20+08:00",
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        price=2488.1,
        bias="flat",
        action="none",
        emitted=False,
    )

    assert text.startswith("[2026-04-05T21:03:20+08:00]")
    assert "策略=Ott2butKAMA" in text
    assert "交易对=ETHUSDT" in text
    assert "当前价=2488.1" in text
    assert "判断=flat" in text
    assert "动作=none" in text
    assert "已发送=否" in text


def test_build_loop_state_from_candles_uses_recent_close_prices():
    from scripts.run_jesse_live_loop import build_loop_state_from_candles

    snapshot = {
        "symbol": "ETHUSDT",
        "close_prices": [2505.0, 2516.8, 2524.1],
        "latest_timestamp": 1712189100000,
        "timestamp": "2026-04-05T21:33:20+08:00",
    }

    state = build_loop_state_from_candles(snapshot)

    assert state["price"] == 2524.1
    assert state["timestamp"] == "2026-04-05T21:33:20+08:00"
    assert state["action"] in {"open_long", "open_short", "close_long", "close_short", "none"}


def test_render_position_summary_contains_floating_pnl_fields():
    from scripts.run_jesse_live_loop import render_position_summary

    position = {
        "side": "long",
        "qty": 5.12,
        "entry_price": 2450.0,
    }

    text = render_position_summary(
        timestamp="2026-04-05T21:03:30+08:00",
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        current_price=2488.1,
        position=position,
        action="hold",
        emitted=False,
    )

    assert text.startswith("[2026-04-05T21:03:30+08:00]")
    assert "持仓方向=多" in text
    assert "持仓数量(ETH)=0.80383" in text
    assert "开仓价=2450.0" in text
    assert "当前价=2488.1" in text
    assert "持仓名义金额(USDT)=2000.01" in text
    assert "浮动盈亏=" in text
    assert "浮动收益率=" in text
    assert "动作=hold" in text


def test_render_flat_summary_contains_account_fields():
    from scripts.run_jesse_live_loop import render_flat_summary

    text = render_flat_summary(
        timestamp="2026-04-05T21:03:20+08:00",
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        price=2057.99,
        bias="flat",
        action="none",
        emitted=False,
        initial_capital=1000.0,
        realized_pnl=35.2,
        unrealized_pnl=0.0,
        current_equity=1035.2,
    )

    assert "初始资金=1000.00" in text
    assert "已实现盈亏=+35.20" in text
    assert "未实现盈亏=+0.00" in text
    assert "当前权益=1035.20" in text


def test_render_position_summary_contains_account_and_notional_fields():
    from scripts.run_jesse_live_loop import render_position_summary

    position = {
        "side": "long",
        "qty": 1.0,
        "entry_price": 2058.05,
    }

    text = render_position_summary(
        timestamp="2026-04-05T21:03:30+08:00",
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        current_price=2057.99,
        position=position,
        action="hold",
        emitted=False,
        initial_capital=1000.0,
        realized_pnl=35.2,
        unrealized_pnl=-0.06,
        current_equity=1035.14,
    )

    assert "持仓数量(ETH)=0.97182" in text
    assert "持仓名义金额(USDT)=2000.00" in text
    assert "已实现盈亏=+35.20" in text
    assert "未实现盈亏=-0.06" in text
    assert "当前权益=1035.14" in text


def test_compute_position_pnl_for_short_position():
    from scripts.run_jesse_live_loop import compute_position_pnl

    position = {
        "side": "short",
        "qty": 2.0,
        "entry_price": 2500.0,
    }

    pnl, pnl_pct = compute_position_pnl(position=position, current_price=2400.0)

    assert pnl == 200.0
    assert pnl_pct == 4.0


def test_build_loop_state_from_market_snapshot_uses_market_price():
    from scripts.run_jesse_live_loop import build_loop_state_from_market_snapshot

    snapshot = {
        "symbol": "ETHUSDT",
        "price": 2516.8,
        "timestamp": "2026-04-05T21:33:20+08:00",
    }

    state = build_loop_state_from_market_snapshot(snapshot)

    assert state["price"] == 2516.8
    assert state["timestamp"] == "2026-04-05T21:33:20+08:00"
    assert state["action"] in {"open_long", "open_short", "close_long", "close_short", "none"}


def test_run_cycle_does_not_emit_signal_when_market_snapshot_fetch_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys):
    import scripts.run_jesse_live_loop as module

    workspace = tmp_path / "runtime" / "jesse_workspace"
    workspace.mkdir(parents=True)

    monkeypatch.setattr(module, "ensure_runtime_ready", lambda: workspace)
    monkeypatch.setattr(module, "prepare_import_path", lambda current: None)
    monkeypatch.setattr(module, "fetch_recent_klines", lambda symbol, interval="5m", limit=50: (_ for _ in ()).throw(RuntimeError("fetch failed")))
    monkeypatch.setattr(module, "emit_strategy_signals", lambda loop_state=None: (_ for _ in ()).throw(AssertionError("should not emit when market fetch fails")))

    module.run_cycle()

    output = capsys.readouterr().out.strip()
    assert "行情获取失败" in output
    assert "持仓方向=" not in output
    assert "当前价=0.0" not in output


def test_print_cycle_summary_uses_persistent_position_for_display(monkeypatch, capsys):
    import scripts.run_jesse_live_loop as module

    loop_state = {
        "timestamp": "2026-04-05T21:33:30+08:00",
        "price": 2488.1,
        "bias": "long",
        "action": "hold",
        "emitted": False,
        "position": {"side": "long", "qty": 1.0, "entry_price": 2508.2},
    }

    monkeypatch.setattr(module, "fetch_persistent_position", lambda symbol: {"side": "long", "qty": 5.12, "entry_price": 2450.0})

    module.print_cycle_summary(loop_state)

    output = capsys.readouterr().out.strip()

    assert "持仓数量(ETH)=0.80383" in output
    assert "持仓名义金额(USDT)=2000.01" in output
    assert "开仓价=2450.0" in output
    assert "当前价=2488.1" in output
