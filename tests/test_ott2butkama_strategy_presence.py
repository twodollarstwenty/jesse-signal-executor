from pathlib import Path


def test_project_has_ott2butkama_strategy_source():
    assert Path("strategies/jesse/Ott2butKAMA/__init__.py").exists()


def test_ott2butkama_risk_managed_strategy_exists():
    strategy_file = Path("strategies/jesse/Ott2butKAMA_RiskManaged/__init__.py")
    assert strategy_file.exists()


def test_ott2butkama_risk_managed25_strategy_exists():
    strategy_file = Path("strategies/jesse/Ott2butKAMA_RiskManaged25/__init__.py")
    assert strategy_file.exists()
