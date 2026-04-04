from pydantic import BaseModel, Field


class Signal(BaseModel):
    strategy: str
    symbol: str
    timeframe: str
    signal_time: str
    action: str
    payload: dict = Field(default_factory=dict)
