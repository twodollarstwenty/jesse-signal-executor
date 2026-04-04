from pathlib import Path


def test_bootstrap_jesse_runtime_script_exists():
    path = Path("scripts/bootstrap_jesse_runtime.sh")
    assert path.exists()
    assert path.read_text().startswith("#!/usr/bin/env bash")
