import datetime
from abc import ABC, abstractmethod
from typing import List

from .models import Bar

class Ingester(ABC):
    """
    Abstract base class for all data providers.
    """
    
    @abstractmethod
    def fetch_data(self, symbol: str, timeframe: str, start: datetime.datetime, end: datetime.datetime) -> List[Bar]:
        """
        Fetches OHLCV data from the provider for the given range.
        
        :param symbol: Ticker symbol (e.g., 'SPY')
        :param timeframe: Requested timeframe (e.g., '1day', '1hr')
        :param start: Start datetime (inclusive)
        :param end: End datetime (inclusive)
        :return: List of Bar objects
        """
        pass
