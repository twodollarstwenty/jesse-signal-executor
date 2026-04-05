import os
import time
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path

from apps.executor_service.service import run_once


def write_heartbeat(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    payload = datetime.now(timezone.utc).isoformat()
    last_error: FileNotFoundError | None = None
    for _ in range(3):
        temp_path.write_text(payload)
        try:
            temp_path.replace(path)
            return
        except FileNotFoundError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error


def parse_positive_interval(raw_value: str, *, env_name: str) -> float:
    try:
        interval = float(raw_value)
    except ValueError as exc:
        raise ValueError(f"{env_name} must be a finite positive number") from exc

    if not isfinite(interval) or interval <= 0:
        raise ValueError(f"{env_name} must be a finite positive number")

    return interval


def main() -> None:
    heartbeat = Path(os.getenv("EXECUTOR_HEARTBEAT_PATH", "/tmp/executor.heartbeat"))
    interval = parse_positive_interval(
        os.getenv("EXECUTOR_POLL_INTERVAL_SECONDS", "1.0"),
        env_name="EXECUTOR_POLL_INTERVAL_SECONDS",
    )

    while True:
        run_once()
        write_heartbeat(heartbeat)
        time.sleep(interval)


if __name__ == "__main__":
    main()
