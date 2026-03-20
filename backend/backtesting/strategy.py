from abc import ABC, abstractmethod
from typing import List, Optional

from .context import MarketContext
from .models import Order

class Strategy(ABC):
    """
    Abstract base class for all trading strategies.
    """
    
    def on_start(self, context: MarketContext) -> None:
        """
        Called once before the backtest loop begins.
        """
        pass
        
    @abstractmethod
    def on_bar(self, context: MarketContext) -> Optional[List[Order]]:
        """
        Called at every new bar.
        Returns a list of orders to execute at the OPEN of the NEXT bar, or None.
        """
        pass
        
    def on_end(self, context: MarketContext) -> None:
        """
        Called once after the backtest loop finishes.
        """
        pass
