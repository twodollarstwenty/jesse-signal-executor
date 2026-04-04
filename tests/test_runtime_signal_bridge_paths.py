from pathlib import Path


def test_runtime_has_strategy_and_bridge_targets():
    assert Path("runtime/jesse_workspace/strategies/Ott2butKAMA/__init__.py").exists()
    assert Path("apps/signal_service/jesse_bridge/emitter.py").exists()
