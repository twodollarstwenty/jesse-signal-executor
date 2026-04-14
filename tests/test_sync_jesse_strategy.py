from scripts.sync_jesse_strategy import build_target_path


def test_build_target_path_points_into_runtime_workspace():
    path = build_target_path("Ott2butKAMA")
    assert "runtime/jesse_workspace/strategies/Ott2butKAMA" in str(path)


def test_build_target_path_supports_risk_managed_variant_name():
    path = build_target_path("Ott2butKAMA_RiskManaged")
    assert "runtime/jesse_workspace/strategies/Ott2butKAMA_RiskManaged" in str(path)


def test_sync_strategy_copies_shared_strategy_support_modules(tmp_path, monkeypatch):
    import scripts.sync_jesse_strategy as module

    monkeypatch.setattr(module, "ROOT", tmp_path)

    strategy_source = tmp_path / "strategies" / "jesse" / "Ott2butKAMA"
    strategy_source.mkdir(parents=True)
    (strategy_source / "__init__.py").write_text("# strategy")

    shared_source = tmp_path / "strategies" / "shared"
    shared_source.mkdir(parents=True)
    (shared_source / "ott2butkama_core.py").write_text("CORE = True")
    (shared_source / "ott2butkama_features.py").write_text("FEATURES = True")

    for directory_name in ("custom_indicators_ottkama", "custom_indicators"):
        source = tmp_path / "strategies" / "jesse" / directory_name
        source.mkdir(parents=True)
        (source / "__init__.py").write_text("# indicator")

    module.sync_strategy("Ott2butKAMA")

    runtime_shared = tmp_path / "runtime" / "jesse_workspace" / "strategies" / "shared"
    assert (runtime_shared / "ott2butkama_core.py").exists()
    assert (runtime_shared / "ott2butkama_features.py").exists()


def test_build_target_path_supports_risk_managed25_variant_name():
    path = build_target_path("Ott2butKAMA_RiskManaged25")
    assert "runtime/jesse_workspace/strategies/Ott2butKAMA_RiskManaged25" in str(path)


def test_build_target_path_supports_risk_managed25_grid_variant_name():
    path = build_target_path("Ott2butKAMA_RiskManaged25_Grid")
    assert "runtime/jesse_workspace/strategies/Ott2butKAMA_RiskManaged25_Grid" in str(path)


def test_runtime_indicator_dirs_exist_after_sync_layout():
    from pathlib import Path

    assert Path("runtime/jesse_workspace/custom_indicators_ottkama").exists()
    assert Path("runtime/jesse_workspace/custom_indicators").exists()


def test_sync_strategy_copies_shared_indicator_package_subtree(tmp_path, monkeypatch):
    import scripts.sync_jesse_strategy as module

    monkeypatch.setattr(module, "ROOT", tmp_path)

    strategy_source = tmp_path / "strategies" / "jesse" / "Ott2butKAMA"
    strategy_source.mkdir(parents=True)
    (strategy_source / "__init__.py").write_text("# strategy")

    shared_core = tmp_path / "strategies" / "shared"
    shared_core.mkdir(parents=True)
    (shared_core / "ott2butkama_core.py").write_text("CORE = True")
    (shared_core / "ott2butkama_features.py").write_text("FEATURES = True")

    shared_indicator_pkg = shared_core / "custom_indicators_ottkama"
    shared_indicator_pkg.mkdir()
    (shared_indicator_pkg / "__init__.py").write_text("INDICATOR = True")

    for directory_name in ("custom_indicators_ottkama", "custom_indicators"):
        source = tmp_path / "strategies" / "jesse" / directory_name
        source.mkdir(parents=True)
        (source / "__init__.py").write_text("# indicator")

    module.sync_strategy("Ott2butKAMA")

    runtime_pkg = tmp_path / "runtime" / "jesse_workspace" / "strategies" / "shared" / "custom_indicators_ottkama"
    assert (runtime_pkg / "__init__.py").exists()


def test_sync_strategies_copies_each_unique_strategy_once(tmp_path, monkeypatch):
    import scripts.sync_jesse_strategy as module

    monkeypatch.setattr(module, "ROOT", tmp_path)
    calls: list[str] = []

    def record_sync(strategy_name: str) -> None:
        calls.append(strategy_name)

    for name in ("Ott2butKAMA", "Ott2butKAMA_RiskManaged25"):
        strategy_source = tmp_path / "strategies" / "jesse" / name
        strategy_source.mkdir(parents=True)
        (strategy_source / "__init__.py").write_text(f"# {name}")

    shared_source = tmp_path / "strategies" / "shared"
    shared_source.mkdir(parents=True)
    (shared_source / "ott2butkama_core.py").write_text("CORE = True")
    (shared_source / "ott2butkama_features.py").write_text("FEATURES = True")

    for directory_name in ("custom_indicators_ottkama", "custom_indicators"):
        source = tmp_path / "strategies" / "jesse" / directory_name
        source.mkdir(parents=True)
        (source / "__init__.py").write_text("# indicator")

    monkeypatch.setattr(module, "sync_strategy", record_sync)

    module.sync_strategies(["Ott2butKAMA", "Ott2butKAMA", "Ott2butKAMA_RiskManaged25"])

    assert calls == ["Ott2butKAMA", "Ott2butKAMA_RiskManaged25"]
