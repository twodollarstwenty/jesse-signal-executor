from pydantic import BaseModel


class Settings(BaseModel):
    exchange: str = "binance_perpetual_futures"
    execution_mode: str = "dry_run"
    default_symbol: str = "ETHUSDT"
