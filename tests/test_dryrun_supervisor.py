from pathlib import Path


def test_build_supervisor_status_reports_mixed_instance_health(tmp_path: Path):
    from scripts.run_dryrun_supervisor import build_supervisor_status

    runtime_root = tmp_path / "runtime"
    (runtime_root / "supervisor" / "pids").mkdir(parents=True)
    (runtime_root / "supervisor" / "pids" / "supervisor.pid").write_text("123\n")
    health = {
        "ott_eth_5m": {"state": "running"},
        "risk25_sol_5m": {"state": "failed"},
    }

    status = build_supervisor_status(runtime_root=runtime_root, instance_health=health)

    assert status["supervisor"] == "degraded"
    assert status["instances_total"] == 2
    assert status["instances_running"] == 1
    assert status["instances_failed"] == 1


def test_ensure_supervisor_layout_creates_supervisor_runtime_directories(tmp_path: Path):
    from scripts.run_dryrun_supervisor import ensure_supervisor_layout

    runtime_root = tmp_path / "runtime"

    ensure_supervisor_layout(runtime_root)

    assert (runtime_root / "supervisor" / "logs").exists()
    assert (runtime_root / "supervisor" / "pids").exists()


def test_main_start_ensures_layout_loads_instances_and_syncs_unique_strategies(monkeypatch, tmp_path: Path):
    import scripts.run_dryrun_supervisor as module

    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    config_path = tmp_path / "instances.yaml"
    calls: dict[str, object] = {}

    instances = [
        type("Instance", (), {"id": "ott_eth_5m", "strategy": "Ott2butKAMA"})(),
        type("Instance", (), {"id": "ott_btc_5m", "strategy": "Ott2butKAMA"})(),
        type("Instance", (), {"id": "risk25_sol_5m", "strategy": "Ott2butKAMA_RiskManaged25"})(),
    ]

    monkeypatch.setenv("REPO_ROOT", str(repo_root))
    monkeypatch.setenv("DRYRUN_RUNTIME_DIR", str(runtime_root))
    monkeypatch.setenv("DRYRUN_INSTANCES_CONFIG", str(config_path))
    def fake_ensure_supervisor_layout(path: Path) -> None:
        calls["layout"] = path

    def fake_load_instances(path: Path):
        calls["config"] = path
        return instances

    def fake_sync_strategies(names: list[str]) -> None:
        calls["strategies"] = list(names)

    def fake_start_instance_workers(**kwargs):
        calls["workers"] = [instance.id for instance in kwargs["instances"]]

    monkeypatch.setattr(module, "ensure_supervisor_layout", fake_ensure_supervisor_layout)
    monkeypatch.setattr(module, "load_instances", fake_load_instances)
    monkeypatch.setattr(module, "sync_strategies", fake_sync_strategies)
    monkeypatch.setattr(module, "start_instance_workers", fake_start_instance_workers)

    module.main(["start"])

    assert calls["layout"] == runtime_root
    assert calls["config"] == config_path
    assert calls["strategies"] == ["Ott2butKAMA", "Ott2butKAMA_RiskManaged25"]
    assert calls["workers"] == ["ott_eth_5m", "ott_btc_5m", "risk25_sol_5m"]


def test_main_start_writes_supervisor_pid_file(monkeypatch, tmp_path: Path):
    import scripts.run_dryrun_supervisor as module

    runtime_root = tmp_path / "runtime"
    config_path = tmp_path / "instances.yaml"
    instances = [type("Instance", (), {"id": "ott_eth_5m", "strategy": "Ott2butKAMA"})()]

    monkeypatch.setenv("DRYRUN_RUNTIME_DIR", str(runtime_root))
    monkeypatch.setenv("DRYRUN_INSTANCES_CONFIG", str(config_path))
    monkeypatch.setattr(module, "load_instances", lambda path: instances)
    monkeypatch.setattr(module, "sync_strategies", lambda names: None)
    monkeypatch.setattr(module, "start_instance_workers", lambda **kwargs: None)

    module.main(["start"])

    pid_file = runtime_root / "supervisor" / "pids" / "supervisor.pid"
    assert pid_file.exists()
    assert pid_file.read_text().strip().isdigit()


def test_main_stop_removes_supervisor_pid_file(monkeypatch, tmp_path: Path):
    import scripts.run_dryrun_supervisor as module

    runtime_root = tmp_path / "runtime"
    pid_dir = runtime_root / "supervisor" / "pids"
    pid_dir.mkdir(parents=True)
    (pid_dir / "supervisor.pid").write_text("12345")

    instances = [type("Instance", (), {"id": "ott_eth_5m", "strategy": "Ott2butKAMA"})()]
    calls: list[str] = []
    monkeypatch.setenv("DRYRUN_RUNTIME_DIR", str(runtime_root))
    monkeypatch.setattr(module, "load_instances", lambda path: calls.append("load") or instances)
    monkeypatch.setattr(module, "sync_strategies", lambda names: calls.append("sync"))
    monkeypatch.setattr(module, "stop_instance_workers", lambda **kwargs: calls.append("stop-workers"))

    module.main(["stop"])

    assert not (pid_dir / "supervisor.pid").exists()
    assert calls == ["load", "stop-workers"]


def test_main_status_does_not_trigger_strategy_sync(monkeypatch, tmp_path: Path):
    import scripts.run_dryrun_supervisor as module

    runtime_root = tmp_path / "runtime"
    config_path = tmp_path / "instances.yaml"
    instances = [type("Instance", (), {"id": "ott_eth_5m", "strategy": "Ott2butKAMA"})()]
    calls: list[str] = []

    monkeypatch.setenv("DRYRUN_RUNTIME_DIR", str(runtime_root))
    monkeypatch.setenv("DRYRUN_INSTANCES_CONFIG", str(config_path))
    monkeypatch.setattr(module, "load_instances", lambda path: calls.append("load") or instances)
    monkeypatch.setattr(module, "sync_strategies", lambda names: calls.append("sync"))

    module.main(["status"])

    assert calls == ["load"]


def test_build_supervisor_status_reports_stopped_without_pid_marker(tmp_path: Path):
    from scripts.run_dryrun_supervisor import build_supervisor_status

    runtime_root = tmp_path / "runtime"
    health = {"ott_eth_5m": {"state": "stopped"}}

    status = build_supervisor_status(runtime_root=runtime_root, instance_health=health)

    assert status["supervisor"] == "stopped"


def test_main_start_cleans_up_pid_file_when_initialization_fails(monkeypatch, tmp_path: Path):
    import pytest
    import scripts.run_dryrun_supervisor as module

    runtime_root = tmp_path / "runtime"
    config_path = tmp_path / "instances.yaml"

    monkeypatch.setenv("DRYRUN_RUNTIME_DIR", str(runtime_root))
    monkeypatch.setenv("DRYRUN_INSTANCES_CONFIG", str(config_path))
    monkeypatch.setattr(module, "load_instances", lambda path: (_ for _ in ()).throw(RuntimeError("boom")))

    with pytest.raises(RuntimeError, match="boom"):
        module.main(["start"])

    assert not (runtime_root / "supervisor" / "pids" / "supervisor.pid").exists()


def test_start_instance_workers_spawns_worker_process_and_writes_instance_pid(monkeypatch, tmp_path: Path):
    import scripts.run_dryrun_supervisor as module

    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    config_path = tmp_path / "instances.yaml"
    repo_root.mkdir(parents=True)
    (repo_root / "scripts").mkdir(parents=True)

    calls: list[tuple[list[str], dict]] = []

    class FakeProcess:
        def __init__(self, pid: int):
            self.pid = pid

    def fake_popen(command, stdout, stderr, env, start_new_session):
        calls.append((command, env))
        return FakeProcess(43210)

    monkeypatch.setattr(module.subprocess, "Popen", fake_popen)

    instances = [type("Instance", (), {"id": "ott_eth_5m", "strategy": "Ott2butKAMA"})()]

    module.start_instance_workers(
        repo_root=repo_root,
        runtime_root=runtime_root,
        config_path=config_path,
        instances=instances,
    )

    pid_path = runtime_root / "supervisor" / "pids" / "ott_eth_5m.pid"
    assert pid_path.exists()
    assert pid_path.read_text().strip() == "43210"
    assert calls[0][1]["DRYRUN_INSTANCE_ID"] == "ott_eth_5m"
    assert calls[0][1]["DRYRUN_INSTANCE_RUN_ONCE"] == "0"


def test_stop_instance_workers_terminates_process_and_removes_pid(monkeypatch, tmp_path: Path):
    import scripts.run_dryrun_supervisor as module

    runtime_root = tmp_path / "runtime"
    pid_path = runtime_root / "supervisor" / "pids" / "ott_eth_5m.pid"
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text("23456\n")

    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(module, "is_process_alive", lambda pid: True)
    monkeypatch.setattr(module, "wait_for_process_exit", lambda pid, timeout_seconds=2.0: True)
    monkeypatch.setattr(module.os, "kill", lambda pid, sig: calls.append((pid, sig)))

    instances = [type("Instance", (), {"id": "ott_eth_5m", "strategy": "Ott2butKAMA"})()]

    module.stop_instance_workers(runtime_root=runtime_root, instances=instances)

    assert calls == [(23456, module.signal.SIGTERM)]
    assert not pid_path.exists()
