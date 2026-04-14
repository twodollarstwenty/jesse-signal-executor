from pathlib import Path


def test_main_loads_selected_instance_and_runs_one_cycle(monkeypatch):
    import scripts.run_strategy_instance as module

    calls = []
    instance = type(
        "Instance",
        (),
        {
            "id": "ott_eth_5m",
            "strategy": "Ott2butKAMA",
            "symbol": "ETHUSDT",
            "timeframe": "5m",
            "capital_usdt": 1000,
            "sizing": {"mode": "fixed_fraction", "position_fraction": 0.2, "leverage": 10},
            "model_dump": lambda self: {
                "id": "ott_eth_5m",
                "strategy": "Ott2butKAMA",
                "symbol": "ETHUSDT",
                "timeframe": "5m",
                "capital_usdt": 1000,
                "sizing": {"mode": "fixed_fraction", "position_fraction": 0.2, "leverage": 10},
            },
        },
    )()
    context = {"instance_id": "ott_eth_5m"}

    monkeypatch.setattr(module, "load_instances", lambda path: [instance])
    monkeypatch.setattr(module, "build_runtime_context", lambda instance, runtime_root: calls.append((instance, runtime_root)) or context)
    monkeypatch.setattr(module, "run_cycle", lambda context=None: calls.append(context))
    monkeypatch.setenv("DRYRUN_INSTANCE_ID", "ott_eth_5m")

    module.main()

    assert calls[0][0] == instance.model_dump()
    assert isinstance(calls[0][1], Path)
    assert calls[1] is context


def test_main_uses_environment_overrides_for_repo_root_runtime_dir_and_config(monkeypatch):
    import scripts.run_strategy_instance as module

    calls = []
    repo_root = Path("/tmp/custom-repo")
    runtime_root = Path("/tmp/custom-runtime")
    config_path = Path("/tmp/custom-config.yaml")
    instance = type(
        "Instance",
        (),
        {
            "id": "ott_eth_5m",
            "strategy": "Ott2butKAMA",
            "symbol": "ETHUSDT",
            "timeframe": "5m",
            "capital_usdt": 1000,
            "sizing": {"mode": "fixed_fraction", "position_fraction": 0.2, "leverage": 10},
            "model_dump": lambda self: {
                "id": "ott_eth_5m",
                "strategy": "Ott2butKAMA",
                "symbol": "ETHUSDT",
                "timeframe": "5m",
                "capital_usdt": 1000,
                "sizing": {"mode": "fixed_fraction", "position_fraction": 0.2, "leverage": 10},
            },
        },
    )()
    context = {"instance_id": "ott_eth_5m"}

    monkeypatch.setattr(module, "load_instances", lambda path: calls.append(path) or [instance])
    monkeypatch.setattr(module, "build_runtime_context", lambda instance, runtime_root: calls.append((instance, runtime_root)) or context)
    monkeypatch.setattr(module, "run_cycle", lambda context=None: calls.append(context))
    monkeypatch.setenv("DRYRUN_INSTANCE_ID", "ott_eth_5m")
    monkeypatch.setenv("REPO_ROOT", str(repo_root))
    monkeypatch.setenv("DRYRUN_RUNTIME_DIR", str(runtime_root))
    monkeypatch.setenv("DRYRUN_INSTANCES_CONFIG", str(config_path))

    module.main()

    assert calls[0] == config_path
    assert calls[1] == (instance.model_dump(), runtime_root)
    assert calls[2] is context
