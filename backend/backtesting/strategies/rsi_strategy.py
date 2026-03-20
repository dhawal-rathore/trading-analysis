import pandas as pd
from typing import List, Optional

from backtesting.strategy import Strategy
from backtesting.context import MarketContext
from backtesting.models import Order, OrderSide

class RSIStrategy(Strategy):
    """
    A simple Relative Strength Index (RSI) mean-reversion strategy.
    
    Rules:
    - BUY when RSI drops below lower_bound (e.g. oversold) and we have no position.
    - SELL when RSI rises above upper_bound (e.g. overbought) and we have a position.
    """
    def __init__(self, rsi_period: int = 14, lower_bound: float = 30.0, upper_bound: float = 70.0, position_size: int = 10):
        self.rsi_period = rsi_period
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.position_size = position_size

    def calculate_rsi(self, history) -> float:
        """
        Calculates the latest RSI value using pandas.
        Requires at least rsi_period + 1 bars of history.
        """
        closes = [bar.close for bar in history]
        s = pd.Series(closes)
        
        # Calculate price changes
        delta = s.diff()
        
        # Make two series: one for gains, one for losses
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        
        # Calculate the Exponential Moving Average of gains and losses
        # Using Wilder's smoothing method (alpha=1/period)
        ema_up = up.ewm(com=self.rsi_period - 1, adjust=False).mean()
        ema_down = down.ewm(com=self.rsi_period - 1, adjust=False).mean()
        
        # Calculate Relative Strength (RS)
        rs = ema_up / ema_down
        
        # Calculate RSI
        rsi = 100 - (100 / (1 + rs))
        
        # Return the most recent RSI value
        return rsi.iloc[-1]

    def on_bar(self, context: MarketContext) -> Optional[List[Order]]:
        # We need at least rsi_period + 1 bars to calculate a valid RSI
        if len(context.history) < self.rsi_period:
            return None

        # Combine history with the current bar to get the latest close price included
        full_history = context.history + [context.current_bar]
        
        current_rsi = self.calculate_rsi(full_history)
        
        # Handle cases where RSI calculation might return NaN (e.g. no price movement)
        if pd.isna(current_rsi):
            return None
            
        symbol = context.current_bar.symbol
        current_position = context.portfolio.positions.get(symbol, 0)

        # Logic
        if current_rsi < self.lower_bound and current_position == 0:
            return [Order(symbol, OrderSide.BUY, self.position_size)]
            
        elif current_rsi > self.upper_bound and current_position > 0:
            # Sell the entire position
            return [Order(symbol, OrderSide.SELL, current_position)]
            
        return None
