import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_makefile_target(target: str) -> list[str]:
    recipe_lines = []
    in_target = False

    for line in (REPO_ROOT / "Makefile").read_text().splitlines():
        if not in_target:
            in_target = line == f"{target}:"
            continue

        if line.startswith((" ", "\t")):
            recipe_lines.append(line.strip())
            continue

        break

    return recipe_lines


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


def test_makefile_mentions_instance_worker_logs():
    dryrun_log_recipe = read_makefile_target("dryrun-log")

    assert any(
        "runtime/dryrun/instances/*/logs/worker.log" in line
        for line in dryrun_log_recipe
    )


def test_makefile_mentions_supervisor_pid_cleanup():
    dryrun_reset_recipe = read_makefile_target("dryrun-reset")

    assert any(
        "rm -f runtime/dryrun/supervisor/pids/*.pid" in line
        for line in dryrun_reset_recipe
    )
    assert any(
        "rm -f runtime/dryrun/instances/*/logs/*.log" in line
        for line in dryrun_reset_recipe
    )
    assert all("run_executor_loop.py" not in line for line in dryrun_reset_recipe)
    assert all(
        "run_jesse_dryrun_loop.py" not in line for line in dryrun_reset_recipe
    )


def test_dryrun_log_exits_cleanly_when_no_worker_logs_exist(tmp_path):
    completed = subprocess.run(
        ["make", "-f", str(REPO_ROOT / "Makefile"), "dryrun-log"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "No dry-run worker logs found" in completed.stdout
