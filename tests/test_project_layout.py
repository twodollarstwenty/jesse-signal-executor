from pathlib import Path


def test_project_runtime_files_exist():
    assert Path("apps/signal_service/main.py").exists()
    assert Path("apps/executor_service/main.py").exists()
    assert Path("apps/shared/settings.py").exists()
