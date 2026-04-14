from pathlib import Path


def build_instance_root(runtime_root: Path, instance_id: str) -> Path:
    return runtime_root / "instances" / instance_id


def build_instance_paths(runtime_root: Path, instance_id: str) -> dict[str, Path]:
    root = build_instance_root(runtime_root, instance_id)
    return {
        "root": root,
        "log": root / "logs" / "worker.log",
        "heartbeat": root / "heartbeats" / "worker.heartbeat",
        "last_action": root / "state" / "last_action.txt",
        "last_candle": root / "state" / "last_candle_ts.txt",
    }
