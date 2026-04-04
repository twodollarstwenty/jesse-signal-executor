from scripts.sync_jesse_strategy import build_target_path


def test_build_target_path_points_into_runtime_workspace():
    path = build_target_path("Ott2butKAMA")
    assert "runtime/jesse_workspace/strategies/Ott2butKAMA" in str(path)


def test_runtime_indicator_dirs_exist_after_sync_layout():
    from pathlib import Path

    assert Path("runtime/jesse_workspace/custom_indicators_ottkama").exists()
    assert Path("runtime/jesse_workspace/custom_indicators").exists()
