from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


SizingMode = Literal["fixed_fraction", "fixed_notional", "risk_per_trade"]


class SizingConfig(BaseModel):
    mode: SizingMode
    position_fraction: float | None = Field(default=None, gt=0, le=1)
    leverage: float | None = Field(default=None, gt=0)
    notional_usdt: float | None = Field(default=None, gt=0)
    risk_fraction: float | None = Field(default=None, gt=0, le=1)
    risk_bps: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_mode_fields(self):
        if self.mode == "fixed_fraction" and self.position_fraction is None:
            raise ValueError("fixed_fraction sizing requires position_fraction")
        if self.mode == "fixed_notional" and self.notional_usdt is None:
            raise ValueError("fixed_notional sizing requires notional_usdt")
        if self.mode == "risk_per_trade" and self.risk_fraction is None and self.risk_bps is None:
            raise ValueError("risk_per_trade sizing requires risk_fraction or risk_bps")
        return self


class InstanceConfig(BaseModel):
    id: str
    enabled: bool = True
    strategy: str
    symbol: str
    timeframe: str = "5m"
    capital_usdt: float = Field(gt=0)
    sizing: SizingConfig


class InstanceConfigFile(BaseModel):
    instances: list[InstanceConfig]


def load_instances(config_path: Path) -> list[InstanceConfig]:
    raw = yaml.safe_load(config_path.read_text()) or {}
    parsed = InstanceConfigFile.model_validate(raw)
    enabled_instances = [instance for instance in parsed.instances if instance.enabled]
    seen_ids: set[str] = set()
    for instance in enabled_instances:
        if instance.id in seen_ids:
            raise ValueError(f"duplicate instance id: {instance.id}")
        seen_ids.add(instance.id)
    return enabled_instances
