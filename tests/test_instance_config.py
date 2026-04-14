from pathlib import Path

import pytest


def test_load_instances_reads_enabled_instance_config(tmp_path: Path):
    from apps.runtime.instance_config import load_instances

    config_path = tmp_path / "dryrun_instances.yaml"
    config_path.write_text(
        """
instances:
  - id: ott_eth_5m
    enabled: true
    strategy: Ott2butKAMA
    symbol: ETHUSDT
    timeframe: 5m
    capital_usdt: 1000
    sizing:
      mode: fixed_fraction
      position_fraction: 0.2
      leverage: 10
  - id: disabled_case
    enabled: false
    strategy: Ott2butKAMA
    symbol: BTCUSDT
    timeframe: 5m
    capital_usdt: 1000
    sizing:
      mode: fixed_notional
      notional_usdt: 250
""".strip()
    )

    instances = load_instances(config_path)

    assert [instance.id for instance in instances] == ["ott_eth_5m"]
    assert instances[0].strategy == "Ott2butKAMA"
    assert instances[0].sizing.mode == "fixed_fraction"


def test_load_instances_rejects_duplicate_ids(tmp_path: Path):
    from apps.runtime.instance_config import load_instances

    config_path = tmp_path / "dryrun_instances.yaml"
    config_path.write_text(
        """
instances:
  - id: duplicate
    enabled: true
    strategy: Ott2butKAMA
    symbol: ETHUSDT
    timeframe: 5m
    capital_usdt: 1000
    sizing:
      mode: fixed_fraction
      position_fraction: 0.2
  - id: duplicate
    enabled: true
    strategy: Ott2butKAMA_RiskManaged25
    symbol: SOLUSDT
    timeframe: 5m
    capital_usdt: 1200
    sizing:
      mode: risk_per_trade
      risk_fraction: 0.025
""".strip()
    )

    with pytest.raises(ValueError, match="duplicate instance id"):
        load_instances(config_path)


def test_load_instances_allows_duplicate_ids_when_only_one_is_enabled(tmp_path: Path):
    from apps.runtime.instance_config import load_instances

    config_path = tmp_path / "dryrun_instances.yaml"
    config_path.write_text(
        """
instances:
  - id: duplicate
    enabled: true
    strategy: Ott2butKAMA
    symbol: ETHUSDT
    timeframe: 5m
    capital_usdt: 1000
    sizing:
      mode: fixed_fraction
      position_fraction: 0.2
  - id: duplicate
    enabled: false
    strategy: Ott2butKAMA_RiskManaged25
    symbol: SOLUSDT
    timeframe: 5m
    capital_usdt: 1200
    sizing:
      mode: fixed_notional
      notional_usdt: 250
""".strip()
    )

    instances = load_instances(config_path)

    assert [instance.id for instance in instances] == ["duplicate"]
    assert instances[0].strategy == "Ott2butKAMA"


def test_load_instances_rejects_invalid_sizing_block(tmp_path: Path):
    from apps.runtime.instance_config import load_instances

    config_path = tmp_path / "dryrun_instances.yaml"
    config_path.write_text(
        """
instances:
  - id: broken_risk
    enabled: true
    strategy: Ott2butKAMA_RiskManaged25
    symbol: SOLUSDT
    timeframe: 5m
    capital_usdt: 1200
    sizing:
      mode: risk_per_trade
""".strip()
    )

    with pytest.raises(ValueError, match="risk_per_trade"):
        load_instances(config_path)


@pytest.mark.parametrize(
    ("sizing_block", "message"),
    [
        ("mode: fixed_fraction\n      position_fraction: 0", "position_fraction"),
        ("mode: fixed_fraction\n      position_fraction: 1.1", "position_fraction"),
        (
            "mode: fixed_fraction\n      position_fraction: 0.2\n      leverage: 0",
            "leverage",
        ),
        ("mode: fixed_notional\n      notional_usdt: 0", "notional_usdt"),
        ("mode: risk_per_trade\n      risk_fraction: 0", "risk_fraction"),
        ("mode: risk_per_trade\n      risk_fraction: 1.1", "risk_fraction"),
        ("mode: risk_per_trade\n      risk_bps: 0", "risk_bps"),
    ],
)
def test_load_instances_rejects_invalid_numeric_sizing_values(
    tmp_path: Path,
    sizing_block: str,
    message: str,
):
    from apps.runtime.instance_config import load_instances

    config_path = tmp_path / "dryrun_instances.yaml"
    config_path.write_text(
        f"""
instances:
  - id: invalid_numeric
    enabled: true
    strategy: Ott2butKAMA
    symbol: ETHUSDT
    timeframe: 5m
    capital_usdt: 1000
    sizing:
      {sizing_block}
""".strip()
    )

    with pytest.raises(ValueError, match=message):
        load_instances(config_path)
