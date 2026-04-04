from pathlib import Path
from runpy import run_path


def test_runtime_has_synced_ott2butkama_strategy():
    assert Path("runtime/jesse_workspace/strategies/Ott2butKAMA/__init__.py").exists()


def test_runtime_backtest_config_and_routes_are_not_empty():
    config_text = Path("runtime/jesse_workspace/config.py").read_text()
    routes_text = Path("runtime/jesse_workspace/routes.py").read_text()

    assert "config =" in config_text
    assert "routes =" in routes_text
    assert "ETH-USDT" in routes_text
    assert "5m" in routes_text

    config = run_path("runtime/jesse_workspace/config.py")["config"]
    routes = run_path("runtime/jesse_workspace/routes.py")["routes"]

    assert isinstance(config, dict)
    assert "app" in config
    assert "env" in config
    assert isinstance(config["env"], dict)
    assert "exchanges" in config["env"]

    assert isinstance(routes, list)
    assert routes
    required_route_keys = {"exchange", "strategy", "symbol", "timeframe"}
    assert all(isinstance(route, dict) and required_route_keys <= route.keys() for route in routes)
