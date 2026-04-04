from pathlib import Path


def test_check_jesse_runtime_script_exists():
    assert Path("scripts/check_jesse_runtime.py").exists()
