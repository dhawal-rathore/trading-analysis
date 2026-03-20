import datetime
from dataclasses import dataclass
from enum import Enum, auto

class OrderSide(Enum):
    BUY = auto()
    SELL = auto()

@dataclass
class Order:
    symbol: str
    side: OrderSide
    quantity: float

@dataclass
class Trade:
    symbol: str
    side: OrderSide
    quantity: float
    fill_price: float
    timestamp: datetime.datetime
    commission: float
    pnl: float

@dataclass
class PortfolioView:
    cash: float
    positions: dict[str, float]
    equity: float
