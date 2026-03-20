import datetime
import logging
from typing import Dict, List, Tuple

from db.manager import OHLCVManager
from ingestion.models import Bar
from .models import OrderSide
from .strategy import Strategy
from .context import MarketContext
from .portfolio import Portfolio
from .results import BacktestResult, calculate_metrics

logger = logging.getLogger(__name__)

class BacktestEngine:
    """
    Executes multiple trading strategies concurrently over historical data for comparison.
    """

    def __init__(self, 
                 strategies: Dict[str, Strategy], 
                 db_manager: OHLCVManager,
                 symbol: str,
                 timeframe: str,
                 start: datetime.datetime,
                 end: datetime.datetime,
                 initial_capital: float = 10000.0,
                 commission_pct: float = 0.001,
                 flat_commission: float = 0.0,
                 lookback: int = 50):
        self.strategies = strategies
        self.db_manager = db_manager
        self.symbol = symbol
        self.timeframe = timeframe
        self.start = start
        self.end = end
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.flat_commission = flat_commission
        self.lookback = lookback

    def run(self) -> Dict[str, BacktestResult]:
        logger.info(f"Loading data for {self.symbol} ({self.timeframe}) from {self.start} to {self.end}")
        
        # 1. Load data from DB
        raw_candles = self.db_manager.get_candles(self.symbol, self.timeframe, self.start, self.end)
        
        # Convert dicts to Bar objects
        bars = [
            Bar(
                symbol=c['symbol'],
                timeframe=c['timeframe'],
                timestamp=c['timestamp'],
                open=float(c['open']),
                high=float(c['high']),
                low=float(c['low']),
                close=float(c['close']),
                volume=float(c['volume'])
            ) for c in raw_candles
        ]

        if len(bars) < max(2, self.lookback + 1):
            raise ValueError(f"Insufficient data returned. Got {len(bars)} bars, need at least {max(2, self.lookback + 1)}")

        logger.info(f"Loaded {len(bars)} bars. Starting simulation for {len(self.strategies)} strategies...")

        # Initialize portfolios and equity tracking for each strategy
        portfolios = {name: Portfolio(self.initial_capital) for name in self.strategies}
        equity_curves = {name: [] for name in self.strategies}
        
        # We need a dict for quick price lookups for portfolio equity calculation
        current_prices = {self.symbol: bars[self.lookback].close}

        # 2. Call on_start hook for all strategies
        for name, strategy in self.strategies.items():
            start_context = MarketContext(
                current_bar=bars[self.lookback],
                history=bars[:self.lookback],
                portfolio=portfolios[name].get_view(current_prices),
                timestamp=bars[self.lookback].timestamp
            )
            strategy.on_start(start_context)

        # 3. Main event loop
        # We stop at len(bars) - 1 because we need bars[i+1] to execute orders (to avoid lookahead bias)
        for i in range(self.lookback, len(bars) - 1):
            current_bar = bars[i]
            history = bars[i - self.lookback : i]
            
            # Update current price for accurate equity tracking (using close price of current bar)
            current_prices[self.symbol] = current_bar.close
            
            next_bar = bars[i+1]
            fill_price = next_bar.open
            
            for name, strategy in self.strategies.items():
                portfolio = portfolios[name]
                context = MarketContext(
                    current_bar=current_bar,
                    history=history,
                    portfolio=portfolio.get_view(current_prices),
                    timestamp=current_bar.timestamp
                )

                # Let strategy generate orders
                orders = strategy.on_bar(context)

                # Process orders
                if orders:
                    # FILL ORDERS AT NEXT BAR OPEN to prevent lookahead bias
                    for order in orders:
                        # Basic sanity check
                        if order.symbol != self.symbol:
                            logger.warning(f"[{name}] Strategy returned order for {order.symbol}, but engine is running on {self.symbol}")
                            continue
                            
                        try:
                            portfolio.execute_order(
                                order=order, 
                                fill_price=fill_price, 
                                timestamp=next_bar.timestamp,
                                commission_pct=self.commission_pct,
                                flat_commission=self.flat_commission
                            )
                        except ValueError as e:
                            logger.warning(f"[{name}] Order rejected at {next_bar.timestamp}: {e}")

                # Record equity snapshot
                # Notice we record equity *after* the current bar closes, incorporating any fills from the morning open
                equity_curves[name].append((current_bar.timestamp, portfolio.equity(current_prices)))

        # Process the final bar for equity tracking (but we don't call on_bar because we can't fill orders anymore)
        final_bar = bars[-1]
        current_prices[self.symbol] = final_bar.close
        
        for name in self.strategies:
            equity_curves[name].append((final_bar.timestamp, portfolios[name].equity(current_prices)))

        # 4. Call on_end hook
        for name, strategy in self.strategies.items():
            end_context = MarketContext(
                current_bar=final_bar,
                history=bars[-(self.lookback + 1) : -1],
                portfolio=portfolios[name].get_view(current_prices),
                timestamp=final_bar.timestamp
            )
            strategy.on_end(end_context)

        logger.info("Simulation complete. Calculating metrics...")
        
        results = {}
        for name in self.strategies:
            results[name] = calculate_metrics(self.initial_capital, equity_curves[name], portfolios[name].trades)
            
        return results
