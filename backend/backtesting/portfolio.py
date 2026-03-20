import datetime
from collections import defaultdict
from typing import Dict, List

from .models import Order, OrderSide, Trade, PortfolioView

class Portfolio:
    """
    Tracks cash and positions during a backtest.
    """
    
    def __init__(self, initial_capital: float = 10000.0):
        self.cash = initial_capital
        self.positions: Dict[str, float] = defaultdict(float)
        self.trades: List[Trade] = []

    def execute_order(self, order: Order, fill_price: float, timestamp: datetime.datetime, 
                      commission_pct: float = 0.0, flat_commission: float = 0.0) -> Trade:
        """
        Executes an order, updates cash/positions, and records a trade.
        Prevents selling more than held (no naked shorting in this basic simulation).
        """
        if order.quantity <= 0:
            raise ValueError(f"Order quantity must be positive. Got {order.quantity}")

        trade_value = order.quantity * fill_price
        commission = (trade_value * commission_pct) + flat_commission

        if order.side == OrderSide.BUY:
            total_cost = trade_value + commission
            if self.cash < total_cost:
                raise ValueError(f"Insufficient funds to buy {order.quantity} {order.symbol}. "
                                 f"Need {total_cost}, have {self.cash}")
            
            self.cash -= total_cost
            self.positions[order.symbol] += order.quantity
            pnl = 0.0  # PNL is realized on sell
            
        elif order.side == OrderSide.SELL:
            current_pos = self.positions[order.symbol]
            if current_pos < order.quantity:
                raise ValueError(f"Cannot short sell. Attempted to sell {order.quantity} {order.symbol}, "
                                 f"but only hold {current_pos}")
            
            net_proceeds = trade_value - commission
            self.cash += net_proceeds
            self.positions[order.symbol] -= order.quantity
            
            # Simple PNL calculation for the trade log
            # True PNL tracking requires average cost basis, which is omitted for simplicity
            # PNL here is just net_proceeds, but in reality it should be proceeds - cost.
            # Since we want to chart simple trade PNLs, we'll return an approximation or just use equity curve.
            # We'll set pnl = 0 for now as true position PNL is reflected in equity curve.
            pnl = 0.0
        else:
            raise ValueError(f"Unknown order side {order.side}")

        trade = Trade(
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            fill_price=fill_price,
            timestamp=timestamp,
            commission=commission,
            pnl=pnl
        )
        self.trades.append(trade)
        return trade

    def equity(self, current_prices: Dict[str, float]) -> float:
        """
        Calculates total portfolio equity (cash + value of open positions).
        """
        position_value = sum(
            qty * current_prices.get(symbol, 0.0)
            for symbol, qty in self.positions.items()
        )
        return self.cash + position_value

    def get_view(self, current_prices: Dict[str, float]) -> PortfolioView:
        """
        Returns a read-only snapshot of the portfolio state.
        """
        return PortfolioView(
            cash=self.cash,
            positions=dict(self.positions),
            equity=self.equity(current_prices)
        )
