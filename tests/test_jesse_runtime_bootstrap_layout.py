from pathlib import Path


def test_jesse_runtime_bootstrap_files_exist():
    assert Path("runtime/jesse_workspace/requirements.txt").exists()
    assert Path("runtime/jesse_workspace/.env.example").exists()
