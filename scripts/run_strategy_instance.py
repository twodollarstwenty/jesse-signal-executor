import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from apps.runtime.instance_config import load_instances
from scripts.run_jesse_live_loop import build_runtime_context, run_cycle
from scripts.run_executor_loop import parse_positive_interval, write_heartbeat


def main() -> None:
    instance_id = os.environ["DRYRUN_INSTANCE_ID"]
    repo_root = Path(os.environ.get("REPO_ROOT", str(ROOT)))
    runtime_root = Path(os.environ.get("DRYRUN_RUNTIME_DIR", str(repo_root / "runtime" / "dryrun")))
    config_path = Path(os.environ.get("DRYRUN_INSTANCES_CONFIG", str(repo_root / "configs" / "dryrun_instances.yaml")))

    instances = load_instances(config_path)
    instance = next(current for current in instances if current.id == instance_id)
    context = build_runtime_context(instance=instance.model_dump(), runtime_root=runtime_root)
    heartbeat_path = context["paths"]["heartbeat"]
    run_once = os.getenv("DRYRUN_INSTANCE_RUN_ONCE", "0") == "1"
    interval = parse_positive_interval(
        os.getenv("DRYRUN_INSTANCE_POLL_INTERVAL_SECONDS", "10.0"),
        env_name="DRYRUN_INSTANCE_POLL_INTERVAL_SECONDS",
    )

    if run_once:
        run_cycle(context=context)
        write_heartbeat(heartbeat_path)
        return

    while True:
        run_cycle(context=context)
        write_heartbeat(heartbeat_path)
        time.sleep(interval)


if __name__ == "__main__":
    main()
