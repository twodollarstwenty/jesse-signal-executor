from pathlib import Path


def test_runtime_has_synced_ott2butkama_strategy():
    assert Path("runtime/jesse_workspace/strategies/Ott2butKAMA/__init__.py").exists()
