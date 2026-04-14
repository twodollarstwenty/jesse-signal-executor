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

    monkeypatch.setattr(module, "ensure_supervisor_layout", fake_ensure_supervisor_layout)
    monkeypatch.setattr(module, "load_instances", fake_load_instances)
    monkeypatch.setattr(module, "sync_strategies", fake_sync_strategies)

    module.main(["start"])

    assert calls["layout"] == runtime_root
    assert calls["config"] == config_path
    assert calls["strategies"] == ["Ott2butKAMA", "Ott2butKAMA_RiskManaged25"]


def test_main_start_writes_supervisor_pid_file(monkeypatch, tmp_path: Path):
    import scripts.run_dryrun_supervisor as module

    runtime_root = tmp_path / "runtime"
    config_path = tmp_path / "instances.yaml"
    instances = [type("Instance", (), {"id": "ott_eth_5m", "strategy": "Ott2butKAMA"})()]

    monkeypatch.setenv("DRYRUN_RUNTIME_DIR", str(runtime_root))
    monkeypatch.setenv("DRYRUN_INSTANCES_CONFIG", str(config_path))
    monkeypatch.setattr(module, "load_instances", lambda path: instances)
    monkeypatch.setattr(module, "sync_strategies", lambda names: None)

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

    calls: list[str] = []
    monkeypatch.setenv("DRYRUN_RUNTIME_DIR", str(runtime_root))
    monkeypatch.setattr(module, "load_instances", lambda path: calls.append("load") or [])
    monkeypatch.setattr(module, "sync_strategies", lambda names: calls.append("sync"))

    module.main(["stop"])

    assert not (pid_dir / "supervisor.pid").exists()
    assert calls == []


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
