from pathlib import Path


def test_verify_jesse_imports_script_exists():
    assert Path("scripts/verify_jesse_imports.py").exists()
