from pathlib import Path
import sys
import types


def _install_ott2butkama_import_stubs():
    if "talib" not in sys.modules:
        talib = types.ModuleType("talib")
        talib.RSI = lambda *args, **kwargs: None
        sys.modules["talib"] = talib

    if "custom_indicators_ottkama" not in sys.modules:
        indicators = types.ModuleType("custom_indicators_ottkama")
        indicators.ott = lambda *args, **kwargs: None
        sys.modules["custom_indicators_ottkama"] = indicators

    if "jesse" not in sys.modules:
        jesse = types.ModuleType("jesse")
        utils = types.ModuleType("jesse.utils")
        utils.size_to_qty = lambda *args, **kwargs: None
        utils.crossed = lambda *args, **kwargs: None
        strategies = types.ModuleType("jesse.strategies")

        class Strategy:
            pass

        def cached(func):
            return func

        strategies.Strategy = Strategy
        strategies.cached = cached
        jesse.utils = utils
        jesse.strategies = strategies
        sys.modules["jesse"] = jesse
        sys.modules["jesse.utils"] = utils
        sys.modules["jesse.strategies"] = strategies


def test_ott2butkama_contains_signal_actions():
    text = Path("strategies/jesse/Ott2butKAMA/__init__.py").read_text()
    assert "open_long" in text
    assert "open_short" in text
    assert "close_long" in text
    assert "close_short" in text


def test_risk_managed_variant_contains_same_signal_actions():
    text = Path("strategies/jesse/Ott2butKAMA_RiskManaged/__init__.py").read_text()
    assert "open_long" in text
    assert "open_short" in text
    assert "close_long" in text
    assert "close_short" in text


def test_risk_managed_variant_uses_distinct_strategy_name():
    text = Path("strategies/jesse/Ott2butKAMA_RiskManaged/__init__.py").read_text()
    assert 'strategy="Ott2butKAMA_RiskManaged"' in text


def test_risk_managed25_variant_contains_same_signal_actions():
    text = Path("strategies/jesse/Ott2butKAMA_RiskManaged25/__init__.py").read_text()
    assert "open_long" in text
    assert "open_short" in text
    assert "close_long" in text
    assert "close_short" in text


def test_risk_managed25_grid_variant_contains_same_signal_actions():
    text = Path("strategies/jesse/Ott2butKAMA_RiskManaged25_Grid/__init__.py").read_text()
    assert "open_long" in text
    assert "open_short" in text
    assert "close_long" in text
    assert "close_short" in text
