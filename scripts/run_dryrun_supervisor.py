import os
import sys
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


def start_supervisor(runtime_root: Path) -> None:
    pid_path = build_supervisor_pid_path(runtime_root)
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(f"{os.getpid()}\n")


def stop_supervisor(runtime_root: Path) -> None:
    build_supervisor_pid_path(runtime_root).unlink(missing_ok=True)


def collect_instance_health(runtime_root: Path, instances: list[object]) -> dict[str, dict]:
    health: dict[str, dict] = {}
    for instance in instances:
        instance_paths = build_instance_paths(runtime_root, instance.id)
        state = "running" if instance_paths["heartbeat"].exists() else "stopped"
        health[instance.id] = {"state": state}
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

        try:
            instances = load_instances(config_path)
            strategy_names: list[str] = []
            seen_strategies: set[str] = set()
            for instance in instances:
                if instance.strategy in seen_strategies:
                    continue
                seen_strategies.add(instance.strategy)
                strategy_names.append(instance.strategy)
            sync_strategies(strategy_names)
            start_supervisor(runtime_root)
        except Exception:
            stop_supervisor(runtime_root)
            raise
        return

    if mode == "stop":
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
