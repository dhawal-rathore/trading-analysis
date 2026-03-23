import pytz
from typing import List, Optional

from backtesting.strategy import Strategy
from backtesting.context import MarketContext
from backtesting.models import Order, OrderSide

class MorningBreakoutStrategy(Strategy):
    """
    Morning Breakout Strategy for 30min data.
    
    Rules:
    - BUY when the first 30 mins (09:30 - 10:00 EST) are positive (Close > Open) 
      AND the day opens at > -0.5% of the previous day's close.
    - SELL at the end of the day (15:30 EST bar).
    """
    def __init__(self, position_size: int = 10, gap_threshold: float = -0.005):
        self.position_size = position_size
        self.gap_threshold = gap_threshold
        self.previous_close = None
        
        # We need an eastern timezone to check market hours
        self.eastern = pytz.timezone('US/Eastern')

    def on_bar(self, context: MarketContext) -> Optional[List[Order]]:
        bar = context.current_bar
        
        # Convert UTC timestamp to Eastern time
        dt_est = bar.timestamp.astimezone(self.eastern)
        
        symbol = bar.symbol
        current_position = context.portfolio.positions.get(symbol, 0)
        
        # Handle End of Day (15:30 EST bar, which closes at 16:00 EST)
        if dt_est.hour == 15 and dt_est.minute == 30:
            # Record today's close as previous_close for tomorrow
            self.previous_close = bar.close
            
            # If we have an open position, sell it to close before the next day
            if current_position > 0:
                return [Order(symbol, OrderSide.SELL, current_position)]
                
        # Handle Start of Day (09:30 EST bar, which closes at 10:00 EST)
        elif dt_est.hour == 9 and dt_est.minute == 30:
            # If we just started the backtest and don't have a previous_close, try to peek back into history
            if self.previous_close is None and len(context.history) > 0:
                # We assume the most recent bar from history (e.g. from the previous day) can give us a close
                # This depends on the engine lookback > 0, otherwise it remains None until day 2
                self.previous_close = context.history[-1].close
                
            # Need a previous close to compare against
            if self.previous_close is not None:
                # Calculate the opening gap
                gap = (bar.open - self.previous_close) / self.previous_close
                
                # Check our two conditions:
                # 1. Opening gap is above threshold
                # 2. First 30 min candle is positive (close > open)
                if gap >= self.gap_threshold and bar.close > bar.open:
                    if current_position == 0:
                        return [Order(symbol, OrderSide.BUY, self.position_size)]

        return None
