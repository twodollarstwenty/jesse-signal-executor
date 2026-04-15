import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_dryrun_start_script_exists():
    assert (REPO_ROOT / "scripts/dryrun_start.sh").exists()


def test_dryrun_stop_script_exists():
    assert (REPO_ROOT / "scripts/dryrun_stop.sh").exists()


def test_dryrun_status_script_exists():
    assert (REPO_ROOT / "scripts/dryrun_status.sh").exists()


def test_dryrun_start_script_delegates_to_supervisor_command(tmp_path):
    runtime_root = tmp_path / "runtime-root"
    env = os.environ.copy()
    env["DRYRUN_RUNTIME_DIR"] = str(runtime_root)
    env["DRYRUN_SKIP_PROCESS_START"] = "1"

    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_start.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert (runtime_root / "supervisor").exists()


def test_dryrun_status_script_uses_project_venv_python(tmp_path):
    runtime_root = tmp_path / "runtime-root"
    env = os.environ.copy()
    env["DRYRUN_RUNTIME_DIR"] = str(runtime_root)

    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_status.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "ModuleNotFoundError: No module named 'yaml'" not in completed.stderr
