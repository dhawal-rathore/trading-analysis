import datetime
from dataclasses import dataclass

@dataclass
class Bar:
    """
    Represents a single OHLCV record.
    """
    symbol: str
    timeframe: str
    timestamp: datetime.datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
