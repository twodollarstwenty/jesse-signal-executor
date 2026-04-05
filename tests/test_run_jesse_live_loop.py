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
    monkeypatch.setattr(module, "emit_strategy_signals", lambda: calls.append(f"emit:{Path.cwd()}"))

    original_cwd = Path.cwd()

    module.run_cycle()

    assert calls == [f"emit:{workspace}"]
    assert Path.cwd() == original_cwd


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

    def fake_new_strategy():
        return strategy

    monkeypatch.setattr(module, "build_strategy_instance", fake_new_strategy)
    monkeypatch.setattr(module, "configure_strategy_for_signal_cycle", lambda current: calls.append("configure"))
    monkeypatch.setattr(module, "drive_strategy_cycle", lambda current, loop_state: calls.append("drive"))

    module.emit_strategy_signals()

    assert calls == ["configure", "drive"]


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

    assert "strategy=Ott2butKAMA" in text
    assert "symbol=ETHUSDT" in text
    assert "price=2488.1" in text
    assert "bias=flat" in text
    assert "action=none" in text
    assert "emitted=no" in text


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

    assert "side=long" in text
    assert "qty=5.12" in text
    assert "entry=2450.0" in text
    assert "price=2488.1" in text
    assert "pnl=" in text
    assert "pnl_pct=" in text
    assert "action=hold" in text


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
