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
    Supports a master clock (one series) and auxiliary series for multi-symbol fills and MTM.
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
                 lookback: int = 50,
                 auxiliary_series: List[Tuple[str, str]] = None):
        self.strategies = strategies
        self.db_manager = db_manager
        self.symbol = symbol  # Master clock symbol
        self.timeframe = timeframe # Master clock timeframe
        self.start = start
        self.end = end
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.flat_commission = flat_commission
        self.lookback = lookback
        self.auxiliary_series = auxiliary_series or []

    def _load_bars(self, symbol: str, timeframe: str) -> List[Bar]:
        raw_candles = self.db_manager.get_candles(symbol, timeframe, self.start, self.end)
        return [
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

    def run(self) -> Dict[str, BacktestResult]:
        logger.info(f"Loading master data for {self.symbol} ({self.timeframe}) from {self.start} to {self.end}")
        master_bars = self._load_bars(self.symbol, self.timeframe)

        if len(master_bars) < max(2, self.lookback + 1):
            raise ValueError(f"Insufficient data returned. Got {len(master_bars)} bars, need at least {max(2, self.lookback + 1)}")

        # Load auxiliary data
        aux_data: Dict[str, List[Bar]] = {}
        for aux_sym, aux_tf in self.auxiliary_series:
            logger.info(f"Loading auxiliary data for {aux_sym} ({aux_tf})")
            aux_data[aux_sym] = self._load_bars(aux_sym, aux_tf)
            
        logger.info(f"Loaded {len(master_bars)} master bars. Starting simulation for {len(self.strategies)} strategies...")

        # Initialize portfolios and equity tracking for each strategy
        portfolios = {name: Portfolio(self.initial_capital) for name in self.strategies}
        equity_curves = {name: [] for name in self.strategies}
        
        # We need a dict for quick price lookups for portfolio equity calculation
        current_prices = {self.symbol: master_bars[self.lookback].close}

        # 2. Call on_start hook for all strategies
        for name, strategy in self.strategies.items():
            start_context = MarketContext(
                current_bar=master_bars[self.lookback],
                history=master_bars[:self.lookback],
                portfolio=portfolios[name].get_view(current_prices),
                timestamp=master_bars[self.lookback].timestamp
            )
            strategy.on_start(start_context)

        # 3. Main event loop
        # We stop at len(master_bars) - 1 because we need master_bars[i+1] to execute orders (to avoid lookahead bias)
        for i in range(self.lookback, len(master_bars) - 1):
            current_bar = master_bars[i]
            history = master_bars[i - self.lookback : i]
            
            # Update current price for accurate equity tracking (using close price of current bar)
            current_prices[self.symbol] = current_bar.close
            
            # Also update current prices from aux data using the last known close <= current master timestamp
            for aux_sym, bars in aux_data.items():
                # Simple linear scan backwards (could be optimized with binary search)
                for b in reversed(bars):
                    if b.timestamp <= current_bar.timestamp:
                        current_prices[aux_sym] = b.close
                        break
            
            next_master_bar = master_bars[i+1]
            fill_boundary = current_bar.timestamp # Orders submitted on this bar fill strictly AFTER this time
            
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
                    for order in orders:
                        fill_price = None
                        fill_time = None

                        if order.symbol == self.symbol and not any(s == self.symbol for s, _ in self.auxiliary_series):
                            # Default behavior: fill on next master bar open
                            fill_price = next_master_bar.open
                            fill_time = next_master_bar.timestamp
                        else:
                            # Fill on the first aux bar strictly AFTER the boundary
                            if order.symbol in aux_data:
                                for b in aux_data[order.symbol]:
                                    if b.timestamp > fill_boundary:
                                        fill_price = b.open
                                        fill_time = b.timestamp
                                        break
                                
                        if fill_price is None:
                            logger.warning(f"[{name}] Could not find fill price for {order.symbol} after {fill_boundary}. Order dropped.")
                            continue
                            
                        try:
                            portfolio.execute_order(
                                order=order, 
                                fill_price=fill_price, 
                                timestamp=fill_time,
                                commission_pct=self.commission_pct,
                                flat_commission=self.flat_commission
                            )
                        except ValueError as e:
                            logger.warning(f"[{name}] Order rejected at {fill_time}: {e}")

                # Record equity snapshot
                # Notice we record equity *after* the current bar closes, incorporating any fills from the morning open
                equity_curves[name].append((current_bar.timestamp, portfolio.equity(current_prices)))

        # Process the final bar for equity tracking (but we don't call on_bar because we can't fill orders anymore)
        final_bar = master_bars[-1]
        current_prices[self.symbol] = final_bar.close
        
        for aux_sym, bars in aux_data.items():
            for b in reversed(bars):
                if b.timestamp <= final_bar.timestamp:
                    current_prices[aux_sym] = b.close
                    break
                    
        for name in self.strategies:
            equity_curves[name].append((final_bar.timestamp, portfolios[name].equity(current_prices)))

        # 4. Call on_end hook
        for name, strategy in self.strategies.items():
            end_context = MarketContext(
                current_bar=final_bar,
                history=master_bars[-(self.lookback + 1) : -1],
                portfolio=portfolios[name].get_view(current_prices),
                timestamp=final_bar.timestamp
            )
            strategy.on_end(end_context)

        logger.info("Simulation complete. Calculating metrics...")
        
        results = {}
        for name in self.strategies:
            results[name] = calculate_metrics(self.initial_capital, equity_curves[name], portfolios[name].trades)
            
        return results
