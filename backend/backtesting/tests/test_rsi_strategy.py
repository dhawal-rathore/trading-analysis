import pytest
import datetime
from unittest.mock import MagicMock

from backtesting.strategies.rsi_strategy import RSIStrategy
from backtesting.context import MarketContext
from backtesting.models import OrderSide, PortfolioView
from ingestion.models import Bar

def create_bar(close_price: float, ts=None) -> Bar:
    if ts is None:
        ts = datetime.datetime.now()
    return Bar(
        symbol="SPY",
        timeframe="1day",
        timestamp=ts,
        open=close_price, # lazy, just use close for open/high/low
        high=close_price,
        low=close_price,
        close=close_price,
        volume=1000
    )

def test_rsi_strategy_insufficient_history():
    strategy = RSIStrategy(rsi_period=14)
    
    # 13 bars history + 1 current bar = 14 total bars
    # This might barely calculate an RSI, but our guard requires > rsi_period history 
    # to have enough to calculate changes.
    history = [create_bar(100.0) for _ in range(10)]
    context = MarketContext(
        current_bar=create_bar(100.0),
        history=history,
        portfolio=PortfolioView(10000, {}, 10000),
        timestamp=datetime.datetime.now()
    )
    
    assert strategy.on_bar(context) is None

def test_rsi_strategy_buy_signal():
    strategy = RSIStrategy(rsi_period=14, lower_bound=30, position_size=10)
    
    # Create a sharp drop to force RSI below 30
    history = [create_bar(150.0) for _ in range(14)] # Steady
    current_bar = create_bar(50.0) # Massive drop
    
    context = MarketContext(
        current_bar=current_bar,
        history=history,
        portfolio=PortfolioView(10000, {}, 10000),
        timestamp=datetime.datetime.now()
    )
    
    orders = strategy.on_bar(context)
    
    assert orders is not None
    assert len(orders) == 1
    assert orders[0].side == OrderSide.BUY
    assert orders[0].quantity == 10

def test_rsi_strategy_sell_signal():
    strategy = RSIStrategy(rsi_period=14, upper_bound=70, position_size=10)
    
    # Create a sharp rise to force RSI above 70
    history = [create_bar(50.0) for _ in range(14)] # Steady
    current_bar = create_bar(150.0) # Massive rise
    
    # Give portfolio an existing position so it can sell
    context = MarketContext(
        current_bar=current_bar,
        history=history,
        portfolio=PortfolioView(10000, {"SPY": 10}, 11500),
        timestamp=datetime.datetime.now()
    )
    
    orders = strategy.on_bar(context)
    
    assert orders is not None
    assert len(orders) == 1
    assert orders[0].side == OrderSide.SELL
    assert orders[0].quantity == 10

def test_rsi_strategy_no_signal_in_middle():
    strategy = RSIStrategy(rsi_period=14, lower_bound=30, upper_bound=70)
    
    # Flat price = RSI ~ 50 (in the middle)
    history = [create_bar(100.0) for _ in range(14)]
    current_bar = create_bar(100.0)
    
    context = MarketContext(
        current_bar=current_bar,
        history=history,
        portfolio=PortfolioView(10000, {}, 10000),
        timestamp=datetime.datetime.now()
    )
    
    orders = strategy.on_bar(context)
    assert orders is None
