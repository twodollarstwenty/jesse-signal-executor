import os
import shlex
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_executor_loop import parse_positive_interval, write_heartbeat
from scripts.sync_jesse_strategy import sync_strategy


def main() -> None:
    heartbeat = Path(os.getenv("JESSE_HEARTBEAT_PATH", "/tmp/jesse-dryrun.heartbeat"))
    interval = parse_positive_interval(
        os.getenv("JESSE_DRYRUN_INTERVAL_SECONDS", "10.0"),
        env_name="JESSE_DRYRUN_INTERVAL_SECONDS",
    )
    command = os.getenv("JESSE_DRYRUN_COMMAND")
    if command is None:
        args = ["python3", str((Path(__file__).resolve().parent / "run_jesse_live_loop.py").resolve())]
    else:
        args = shlex.split(command)

    if not args:
        raise ValueError("JESSE_DRYRUN_COMMAND must not be empty")

    sync_strategy("Ott2butKAMA")

    while True:
        subprocess.run(args, check=True)
        write_heartbeat(heartbeat)
        time.sleep(interval)


if __name__ == "__main__":
    main()
