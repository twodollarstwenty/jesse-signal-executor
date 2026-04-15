import importlib.util
import sys
import types
from pathlib import Path


def test_runtime_ott2butkama_strategy_imports_without_talib(monkeypatch):
    strategy_path = (
        Path(__file__).resolve().parent.parent
        / "runtime"
        / "jesse_workspace"
        / "strategies"
        / "Ott2butKAMA"
        / "__init__.py"
    )
    module_name = "runtime_ott2butkama_strategy_under_test"
    spec = importlib.util.spec_from_file_location(module_name, strategy_path)
    module = importlib.util.module_from_spec(spec)

    monkeypatch.delitem(sys.modules, "talib", raising=False)
    monkeypatch.setitem(sys.modules, "jesse", types.SimpleNamespace(utils=types.SimpleNamespace()))
    monkeypatch.setitem(sys.modules, "jesse.strategies", types.SimpleNamespace(Strategy=object, cached=lambda fn: fn))
    monkeypatch.setitem(sys.modules, "custom_indicators_ottkama", types.SimpleNamespace())
    monkeypatch.setitem(
        sys.modules,
        "apps.signal_service.jesse_bridge.emitter",
        types.SimpleNamespace(emit_signal=lambda **kwargs: None),
    )
    monkeypatch.setitem(
        sys.modules,
        "strategies.shared.ott2butkama_core",
        types.SimpleNamespace(evaluate_direction=lambda **kwargs: "long"),
    )
    monkeypatch.setitem(
        sys.modules,
        "strategies.shared.ott2butkama_features",
        types.SimpleNamespace(build_feature_state=lambda **kwargs: {}),
    )

    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)

    assert hasattr(module, "Ott2butKAMA")
