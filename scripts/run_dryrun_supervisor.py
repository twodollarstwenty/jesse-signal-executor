import os
import signal
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from apps.runtime.instance_runtime import build_instance_paths


def load_instances(config_path: Path):
    from apps.runtime.instance_config import load_instances as load_instances_impl

    return load_instances_impl(config_path)


def sync_strategies(strategy_names: list[str]) -> None:
    from scripts.sync_jesse_strategy import sync_strategies as sync_strategies_impl

    sync_strategies_impl(strategy_names)


def build_supervisor_status(*, runtime_root: Path, instance_health: dict[str, dict]) -> dict:
    supervisor_started = build_supervisor_pid_path(runtime_root).exists()
    running = sum(1 for item in instance_health.values() if item["state"] == "running")
    failed = sum(1 for item in instance_health.values() if item["state"] == "failed")

    if not supervisor_started:
        supervisor = "stopped"
    elif failed:
        supervisor = "degraded"
    else:
        supervisor = "running"

    return {
        "supervisor": supervisor,
        "instances_total": len(instance_health),
        "instances_running": running,
        "instances_failed": failed,
    }


def ensure_supervisor_layout(runtime_root: Path) -> None:
    (runtime_root / "supervisor" / "logs").mkdir(parents=True, exist_ok=True)
    (runtime_root / "supervisor" / "pids").mkdir(parents=True, exist_ok=True)


def build_supervisor_pid_path(runtime_root: Path) -> Path:
    return runtime_root / "supervisor" / "pids" / "supervisor.pid"


def build_instance_pid_path(runtime_root: Path, instance_id: str) -> Path:
    return runtime_root / "supervisor" / "pids" / f"{instance_id}.pid"


def is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def wait_for_process_exit(pid: int, *, timeout_seconds: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not is_process_alive(pid):
            return True
        time.sleep(0.1)
    return not is_process_alive(pid)


def start_supervisor(runtime_root: Path) -> None:
    pid_path = build_supervisor_pid_path(runtime_root)
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(f"{os.getpid()}\n")


def stop_supervisor(runtime_root: Path) -> None:
    build_supervisor_pid_path(runtime_root).unlink(missing_ok=True)


def unique_strategies(instances: list[object]) -> list[str]:
    strategy_names: list[str] = []
    seen_strategies: set[str] = set()
    for instance in instances:
        if instance.strategy in seen_strategies:
            continue
        seen_strategies.add(instance.strategy)
        strategy_names.append(instance.strategy)
    return strategy_names


def start_instance_workers(*, repo_root: Path, runtime_root: Path, config_path: Path, instances: list[object]) -> None:
    python_bin = repo_root / ".venv" / "bin" / "python"
    worker_script = repo_root / "scripts" / "run_strategy_instance.py"

    for instance in instances:
        pid_path = build_instance_pid_path(runtime_root, instance.id)
        if pid_path.exists():
            text = pid_path.read_text().strip()
            if text and text.isdigit() and is_process_alive(int(text)):
                continue
            pid_path.unlink(missing_ok=True)

        instance_paths = build_instance_paths(runtime_root, instance.id)
        log_path = instance_paths["log"]
        log_path.parent.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env.update(
            {
                "REPO_ROOT": str(repo_root),
                "DRYRUN_RUNTIME_DIR": str(runtime_root),
                "DRYRUN_INSTANCES_CONFIG": str(config_path),
                "DRYRUN_INSTANCE_ID": instance.id,
                "DRYRUN_INSTANCE_RUN_ONCE": "0",
            }
        )

        with log_path.open("a") as log_file:
            process = subprocess.Popen(
                [str(python_bin), str(worker_script)],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                env=env,
                start_new_session=True,
            )

        pid_path.parent.mkdir(parents=True, exist_ok=True)
        pid_path.write_text(f"{process.pid}\n")


def stop_instance_workers(*, runtime_root: Path, instances: list[object]) -> None:
    for instance in instances:
        pid_path = build_instance_pid_path(runtime_root, instance.id)
        if not pid_path.exists():
            continue

        text = pid_path.read_text().strip()
        if not text or not text.isdigit():
            pid_path.unlink(missing_ok=True)
            continue

        pid = int(text)
        if not is_process_alive(pid):
            pid_path.unlink(missing_ok=True)
            continue

        os.kill(pid, signal.SIGTERM)
        if not wait_for_process_exit(pid, timeout_seconds=2.0):
            os.kill(pid, signal.SIGKILL)
            wait_for_process_exit(pid, timeout_seconds=1.0)

        pid_path.unlink(missing_ok=True)


def collect_instance_health(runtime_root: Path, instances: list[object]) -> dict[str, dict]:
    health: dict[str, dict] = {}
    for instance in instances:
        pid_path = build_instance_pid_path(runtime_root, instance.id)
        if not pid_path.exists():
            health[instance.id] = {"state": "stopped"}
            continue

        text = pid_path.read_text().strip()
        if not text or not text.isdigit():
            pid_path.unlink(missing_ok=True)
            health[instance.id] = {"state": "stopped"}
            continue

        pid = int(text)
        if is_process_alive(pid):
            health[instance.id] = {"state": "running"}
            continue

        pid_path.unlink(missing_ok=True)
        health[instance.id] = {"state": "stopped"}
    return health


def main(argv: list[str] | None = None) -> None:
    repo_root = Path(os.getenv("REPO_ROOT", ROOT))
    runtime_root = Path(os.getenv("DRYRUN_RUNTIME_DIR", repo_root / "runtime" / "dryrun"))
    config_path = Path(os.getenv("DRYRUN_INSTANCES_CONFIG", repo_root / "configs" / "dryrun_instances.yaml"))
    args = list(sys.argv[1:] if argv is None else argv)
    mode = args[0] if args else "status"

    ensure_supervisor_layout(runtime_root)

    if mode == "start":
        if os.getenv("DRYRUN_SKIP_PROCESS_START") == "1":
            start_supervisor(runtime_root)
            return

        instances: list[object] = []
        try:
            instances = load_instances(config_path)
            sync_strategies(unique_strategies(instances))
            start_instance_workers(
                repo_root=repo_root,
                runtime_root=runtime_root,
                config_path=config_path,
                instances=instances,
            )
            start_supervisor(runtime_root)
        except Exception:
            try:
                stop_instance_workers(runtime_root=runtime_root, instances=instances)
            finally:
                stop_supervisor(runtime_root)
            raise
        return

    if mode == "stop":
        instances = load_instances(config_path)
        stop_instance_workers(runtime_root=runtime_root, instances=instances)
        stop_supervisor(runtime_root)
        return

    if mode == "status":
        instances = load_instances(config_path)
        status = build_supervisor_status(
            runtime_root=runtime_root,
            instance_health=collect_instance_health(runtime_root, instances),
        )
        print(status)
        return

    raise SystemExit(f"unsupported mode: {mode}")


if __name__ == "__main__":
    main()
