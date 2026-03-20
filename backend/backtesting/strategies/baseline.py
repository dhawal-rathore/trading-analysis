import math
from typing import List, Optional

from backtesting.strategy import Strategy
from backtesting.context import MarketContext
from backtesting.models import Order, OrderSide

class BuyAndHoldStrategy(Strategy):
    """
    A simple baseline strategy that buys as many shares as possible on the very first bar
    and holds them until the end of the backtest.
    """
    def __init__(self):
        self.has_bought = False

    def on_bar(self, context: MarketContext) -> Optional[List[Order]]:
        if not self.has_bought:
            self.has_bought = True
            
            symbol = context.current_bar.symbol
            price = context.current_bar.close
            cash = context.portfolio.cash
            
            # Simple assumption: We buy max possible integer shares using current close price.
            # We leave a 2% buffer because the order will fill at the NEXT bar's open price, 
            # and we also need to account for commissions.
            quantity = math.floor(cash * 0.98 / price)
            
            if quantity > 0:
                return [Order(symbol, OrderSide.BUY, float(quantity))]
                
        return None
