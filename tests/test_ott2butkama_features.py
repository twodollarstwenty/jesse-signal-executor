def test_build_feature_state_includes_cross_flags_and_chop_bands(monkeypatch):
    import types
    import sys

    fake_numpy = types.SimpleNamespace(asarray=lambda values, dtype=float: values)
    fake_talib = types.SimpleNamespace(RSI=lambda closes, length: [50.0, 55.0, 60.0, 65.0])
    fake_ott_value = types.SimpleNamespace(mavg=[10.0, 10.0, 10.0, 11.0], ott=[10.0, 10.0, 10.0, 10.5])
    fake_cta = types.SimpleNamespace(ott=lambda closes, ott_len, ott_percent, ma_type="kama", sequential=True: fake_ott_value)

    sys.modules.pop("strategies.shared.ott2butkama_features", None)
    monkeypatch.setitem(sys.modules, "numpy", fake_numpy)
    monkeypatch.setitem(sys.modules, "talib", fake_talib)
    monkeypatch.setitem(sys.modules, "strategies.shared.custom_indicators_ottkama", fake_cta)

    from strategies.shared.ott2butkama_features import build_feature_state

    closes = [2500.0, 2510.0, 2520.0, 2530.0]

    state = build_feature_state(
        closes=closes,
        ott_len=36,
        ott_percent=5.4,
        chop_rsi_len=17,
        chop_bandwidth=144,
    )

    assert "cross_up" in state
    assert "cross_down" in state
    assert "chop_value" in state
    assert state["chop_upper_band"] == 54.4
    assert state["chop_lower_band"] == 45.6


def test_build_feature_state_imports_indicator_from_shared_package(monkeypatch):
    import importlib
    import sys
    import types

    fake_numpy = types.SimpleNamespace(asarray=lambda values, dtype=float: values)
    fake_talib = types.SimpleNamespace(RSI=lambda closes, length: [50.0, 55.0, 60.0, 65.0])
    fake_ott_value = types.SimpleNamespace(mavg=[10.0, 10.0, 10.0, 11.0], ott=[10.0, 10.0, 10.0, 10.5])
    fake_indicator_pkg = types.SimpleNamespace(ott=lambda closes, ott_len, ott_percent, ma_type="kama", sequential=True: fake_ott_value)

    sys.modules.pop("strategies.shared.ott2butkama_features", None)
    monkeypatch.setitem(sys.modules, "numpy", fake_numpy)
    monkeypatch.setitem(sys.modules, "talib", fake_talib)
    monkeypatch.setitem(sys.modules, "strategies.shared.custom_indicators_ottkama", fake_indicator_pkg)

    module = importlib.import_module("strategies.shared.ott2butkama_features")

    state = module.build_feature_state(
        closes=[2500.0, 2510.0, 2520.0, 2530.0],
        ott_len=36,
        ott_percent=5.4,
        chop_rsi_len=17,
        chop_bandwidth=144,
    )

    assert state["cross_up"] is True
