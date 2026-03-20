import datetime
from dataclasses import dataclass
from typing import List
from ingestion.models import Bar
from .models import PortfolioView

@dataclass
class MarketContext:
    """
    State passed to a strategy at every tick.
    """
    current_bar: Bar
    history: List[Bar]
    portfolio: PortfolioView
    timestamp: datetime.datetime
