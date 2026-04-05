import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


SUCCESSFUL_JESSE_TEST_COMMAND = "python3 -c \"import sys; from pathlib import Path; p = Path(sys.argv[1]); p.parent.mkdir(parents=True, exist_ok=True); p.write_text('ok')\""

LONG_RUNNING_JESSE_TEST_SCRIPT = REPO_ROOT / "tests/fixtures/long_running_jesse_stub.py"


def successful_jesse_command_for(runtime_root: Path) -> str:
    heartbeat_path = runtime_root / "heartbeats" / "jesse-dryrun.heartbeat"
    return f'{SUCCESSFUL_JESSE_TEST_COMMAND} "{heartbeat_path}"'


def test_dryrun_start_script_exists():
    assert (REPO_ROOT / "scripts/dryrun_start.sh").exists()


def test_dryrun_stop_script_exists():
    assert (REPO_ROOT / "scripts/dryrun_stop.sh").exists()


def test_dryrun_status_script_exists():
    assert (REPO_ROOT / "scripts/dryrun_status.sh").exists()


def test_dryrun_start_script_creates_runtime_directories(tmp_path):
    script = REPO_ROOT / "scripts/dryrun_start.sh"
    runtime_root = tmp_path / "runtime-root"
    env = os.environ.copy()
    env["DRYRUN_RUNTIME_DIR"] = str(runtime_root)
    env["DRYRUN_SKIP_PROCESS_START"] = "1"

    completed = subprocess.run(
        ["bash", str(script)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert (runtime_root / "pids").exists()
    assert (runtime_root / "logs").exists()
    assert (runtime_root / "heartbeats").exists()


def test_dryrun_start_script_replaces_mismatched_existing_pid(tmp_path):
    runtime_root = tmp_path / "runtime-root"
    pid_dir = runtime_root / "pids"
    pid_dir.mkdir(parents=True)
    (pid_dir / "executor.pid").write_text(str(os.getpid()))

    env = os.environ.copy()
    env["DRYRUN_RUNTIME_DIR"] = str(runtime_root)
    env["JESSE_DRYRUN_COMMAND"] = successful_jesse_command_for(runtime_root)

    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_start.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    new_pid = (pid_dir / "executor.pid").read_text().strip()
    assert new_pid != str(os.getpid())

    stop_completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_stop.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert stop_completed.returncode == 0


def test_dryrun_start_script_detects_existing_jesse_process_without_pid_file(tmp_path):
    runtime_root = tmp_path / "runtime-root"
    env = os.environ.copy()
    env["DRYRUN_RUNTIME_DIR"] = str(runtime_root)
    heartbeat_path = runtime_root / "heartbeats" / "jesse-dryrun.heartbeat"
    env["JESSE_DRYRUN_COMMAND"] = f'python3 "{LONG_RUNNING_JESSE_TEST_SCRIPT}" "{heartbeat_path}"'

    first = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_start.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert first.returncode == 0

    (runtime_root / "pids" / "jesse-dryrun.pid").unlink()

    second = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_start.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    stop_completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_stop.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert second.returncode != 0
    assert "already running without pid file" in second.stderr
    assert stop_completed.returncode == 0


def test_dryrun_start_script_exports_repo_root_for_python_processes(tmp_path):
    runtime_root = tmp_path / "runtime-root"
    env = os.environ.copy()
    env["DRYRUN_RUNTIME_DIR"] = str(runtime_root)
    env["JESSE_DRYRUN_COMMAND"] = successful_jesse_command_for(runtime_root)

    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_start.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0

    stop_completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_stop.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert stop_completed.returncode == 0
    assert "ModuleNotFoundError" not in (runtime_root / "logs/executor.log").read_text()
    assert "ModuleNotFoundError" not in (runtime_root / "logs/jesse-dryrun.log").read_text()


def test_dryrun_start_script_sets_local_db_defaults_only_when_unset(tmp_path):
    runtime_root = tmp_path / "runtime-root"
    env = os.environ.copy()
    env["DRYRUN_RUNTIME_DIR"] = str(runtime_root)
    env["JESSE_DRYRUN_COMMAND"] = successful_jesse_command_for(runtime_root)

    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_start.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0

    status_completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_status.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    stop_completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_stop.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert status_completed.returncode == 0
    assert "executor: running" in status_completed.stdout
    assert stop_completed.returncode == 0


def test_dryrun_start_script_preserves_explicit_db_env_overrides(tmp_path):
    runtime_root = tmp_path / "runtime-root"
    env = os.environ.copy()
    env["DRYRUN_RUNTIME_DIR"] = str(runtime_root)
    env["POSTGRES_USER"] = "definitely-not-a-real-user"
    env["JESSE_DRYRUN_COMMAND"] = successful_jesse_command_for(runtime_root)

    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_start.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    status_completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_status.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "failed to start executor" in completed.stderr
    assert status_completed.returncode == 0
    assert "executor: stopped" in status_completed.stdout


def test_dryrun_start_script_rolls_back_executor_when_jesse_start_fails(tmp_path):
    runtime_root = tmp_path / "runtime-root"
    env = os.environ.copy()
    env["DRYRUN_RUNTIME_DIR"] = str(runtime_root)
    env["DRYRUN_JESSE_PYTHON"] = str(tmp_path / "missing-python")

    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_start.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    executor_pid = None
    for line in completed.stdout.splitlines():
        if line.startswith("started executor (pid="):
            executor_pid = line.removeprefix("started executor (pid=").removesuffix(")")
            break

    status_completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_status.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "failed to start jesse-dryrun" in completed.stderr
    assert executor_pid is not None
    assert subprocess.run(
        ["ps", "-p", executor_pid],
        capture_output=True,
        text=True,
    ).returncode != 0
    assert not (runtime_root / "pids/executor.pid").exists()
    assert "executor: stopped" in status_completed.stdout


def test_dryrun_status_does_not_report_stale_during_expected_startup_window(tmp_path):
    runtime_root = tmp_path / "runtime-root"
    env = os.environ.copy()
    env["DRYRUN_RUNTIME_DIR"] = str(runtime_root)
    env["JESSE_DRYRUN_COMMAND"] = (
        "python3 -c \"import time; time.sleep(0.6)\""
    )

    started = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_start.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert started.returncode == 0

    status_completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_status.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    stop_completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_stop.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert status_completed.returncode == 0
    assert "stale" not in status_completed.stdout
    assert "warmup" not in status_completed.stdout
    assert "executor: running" in status_completed.stdout
    assert "jesse-dryrun: running" in status_completed.stdout
    assert stop_completed.returncode == 0
