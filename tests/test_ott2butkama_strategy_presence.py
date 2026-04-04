from pathlib import Path


def test_project_has_ott2butkama_strategy_source():
    assert Path("strategies/jesse/Ott2butKAMA/__init__.py").exists()
