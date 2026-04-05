import os
import sys
from importlib import import_module
from contextlib import contextmanager
from pathlib import Path

from scripts.sync_jesse_strategy import sync_strategy


ROOT = Path(__file__).resolve().parents[1]


def build_workspace_path() -> Path:
    return ROOT / "runtime" / "jesse_workspace"


def ensure_runtime_ready() -> Path:
    workspace = build_workspace_path()
    if not workspace.exists():
        raise FileNotFoundError("runtime/jesse_workspace is missing; run bootstrap first")
    if not (workspace / ".venv").exists():
        raise FileNotFoundError("runtime/jesse_workspace/.venv is missing; run bootstrap first")
    return workspace


def prepare_import_path(workspace: Path) -> None:
    desired_paths = [
        str(workspace),
        str(workspace / "strategies"),
        str(ROOT),
        str(ROOT / "strategies" / "jesse"),
    ]
    existing_paths = [path for path in sys.path if path not in desired_paths]
    sys.path[:] = desired_paths + existing_paths


@contextmanager
def workspace_cwd(workspace: Path):
    previous_cwd = Path.cwd()
    try:
        os.chdir(workspace)
        yield
    finally:
        os.chdir(previous_cwd)


def _set_runtime_attr(strategy, name: str, value) -> None:
    descriptor = getattr(type(strategy), name, None)
    if isinstance(descriptor, property) and descriptor.fset is None:
        runtime_overrides = getattr(strategy, "_runtime_overrides", {})
        runtime_overrides[name] = value
        strategy._runtime_overrides = runtime_overrides
        def getter(self, attr=name, original=descriptor):
            overrides = getattr(self, "_runtime_overrides", {})
            if attr in overrides:
                return overrides[attr]
            return original.fget(self)

        setattr(type(strategy), name, property(getter))
        return

    setattr(strategy, name, value)


def build_strategy_instance():
    Ott2butKAMA = import_module("runtime.jesse_workspace.strategies.Ott2butKAMA").Ott2butKAMA

    return object.__new__(Ott2butKAMA)


def configure_strategy_for_signal_cycle(strategy) -> None:
    strategy.symbol = "ETH-USDT"
    strategy.timeframe = "5m"
    strategy.buy = None
    strategy.sell = None
    strategy.liquidate = lambda: None
    _set_runtime_attr(strategy, "pos_size", 1.0)
    _set_runtime_attr(strategy, "current_candle", [1712188800000, 2500.0, 2500.0, 2510.0, 2490.0, 100.0])
    _set_runtime_attr(strategy, "price", 2500.0)
    _set_runtime_attr(strategy, "cross_down", True)
    _set_runtime_attr(strategy, "cross_up", False)
    _set_runtime_attr(strategy, "is_long", True)
    _set_runtime_attr(strategy, "is_short", False)


def drive_strategy_cycle(strategy) -> None:
    strategy.go_long()
    strategy.update_position()


def emit_strategy_signals() -> None:
    strategy = build_strategy_instance()
    configure_strategy_for_signal_cycle(strategy)
    drive_strategy_cycle(strategy)


def run_cycle() -> None:
    workspace = ensure_runtime_ready()
    sync_strategy("Ott2butKAMA")
    prepare_import_path(workspace)
    with workspace_cwd(workspace):
        emit_strategy_signals()


def main() -> None:
    run_cycle()


if __name__ == "__main__":
    main()
