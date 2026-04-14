from pathlib import Path

import pytest


def test_build_instance_root_uses_instances_directory():
    from apps.runtime.instance_runtime import build_instance_root

    runtime_root = Path("/tmp/runtime")

    assert build_instance_root(runtime_root, "ott_eth_5m") == runtime_root / "instances" / "ott_eth_5m"


def test_build_instance_paths_returns_expected_runtime_targets(tmp_path: Path):
    from apps.runtime.instance_runtime import build_instance_paths

    paths = build_instance_paths(tmp_path, "ott_eth_5m")

    assert paths == {
        "root": tmp_path / "instances" / "ott_eth_5m",
        "log": tmp_path / "instances" / "ott_eth_5m" / "logs" / "worker.log",
        "heartbeat": tmp_path / "instances" / "ott_eth_5m" / "heartbeats" / "worker.heartbeat",
        "last_action": tmp_path / "instances" / "ott_eth_5m" / "state" / "last_action.txt",
        "last_candle": tmp_path / "instances" / "ott_eth_5m" / "state" / "last_candle_ts.txt",
    }


def test_fixed_fraction_sizing_uses_capital_fraction_and_leverage():
    from apps.runtime.sizing import compute_order_qty

    qty = compute_order_qty(
        capital_usdt=1000,
        price=2500,
        sizing={"mode": "fixed_fraction", "position_fraction": 0.2, "leverage": 10},
        signal_payload={},
    )

    assert qty == 0.8


def test_fixed_notional_sizing_uses_configured_notional():
    from apps.runtime.sizing import compute_order_qty

    qty = compute_order_qty(
        capital_usdt=1000,
        price=2500,
        sizing={"mode": "fixed_notional", "notional_usdt": 300},
        signal_payload={},
    )

    assert qty == 0.12


def test_risk_per_trade_sizing_requires_stop_price():
    from apps.runtime.sizing import compute_order_qty

    with pytest.raises(ValueError, match="stop_price"):
        compute_order_qty(
            capital_usdt=1200,
            price=100,
            sizing={"mode": "risk_per_trade", "risk_fraction": 0.025},
            signal_payload={},
        )


def test_risk_per_trade_sizing_uses_stop_distance():
    from apps.runtime.sizing import compute_order_qty

    qty = compute_order_qty(
        capital_usdt=1200,
        price=100,
        sizing={"mode": "risk_per_trade", "risk_fraction": 0.025},
        signal_payload={"stop_price": 95},
    )

    assert qty == 6.0


def test_risk_per_trade_sizing_supports_risk_bps():
    from apps.runtime.sizing import compute_order_qty

    qty = compute_order_qty(
        capital_usdt=1200,
        price=100,
        sizing={"mode": "risk_per_trade", "risk_bps": 250},
        signal_payload={"stop_price": 95},
    )

    assert qty == 6.0


def test_risk_per_trade_sizing_requires_risk_config():
    from apps.runtime.sizing import compute_order_qty

    with pytest.raises(ValueError, match="risk_fraction or risk_bps"):
        compute_order_qty(
            capital_usdt=1200,
            price=100,
            sizing={"mode": "risk_per_trade"},
            signal_payload={"stop_price": 95},
        )


def test_compute_order_qty_rejects_non_positive_price():
    from apps.runtime.sizing import compute_order_qty

    with pytest.raises(ValueError, match="price must be positive"):
        compute_order_qty(
            capital_usdt=1000,
            price=0,
            sizing={"mode": "fixed_notional", "notional_usdt": 300},
            signal_payload={},
        )


def test_compute_order_qty_rejects_non_positive_stop_distance():
    from apps.runtime.sizing import compute_order_qty

    with pytest.raises(ValueError, match="positive stop distance"):
        compute_order_qty(
            capital_usdt=1200,
            price=100,
            sizing={"mode": "risk_per_trade", "risk_fraction": 0.025},
            signal_payload={"stop_price": 100},
        )


def test_compute_order_qty_rejects_unsupported_sizing_mode():
    from apps.runtime.sizing import compute_order_qty

    with pytest.raises(ValueError, match="unsupported sizing mode"):
        compute_order_qty(
            capital_usdt=1000,
            price=2500,
            sizing={"mode": "unknown_mode"},
            signal_payload={},
        )
