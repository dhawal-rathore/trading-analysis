import pytest
import datetime
from unittest.mock import MagicMock

from backtesting.engine import BacktestEngine
from backtesting.models import Order, OrderSide
from backtesting.strategy import Strategy
from ingestion.models import Bar

class DummyStrategy(Strategy):
    def __init__(self, orders_to_emit=None):
        self.orders_to_emit = orders_to_emit or []
        self.bar_count = 0
        
    def on_bar(self, context):
        orders = self.orders_to_emit[self.bar_count] if self.bar_count < len(self.orders_to_emit) else None
        self.bar_count += 1
        return orders

@pytest.fixture
def mock_db_manager():
    manager = MagicMock()
    
    # Create 5 days of dummy data
    base_ts = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    bars = []
    for i in range(5):
        # Open=10, High=12, Low=9, Close=11
        bars.append({
            'symbol': 'SPY', 'timeframe': '1day', 'timestamp': base_ts + datetime.timedelta(days=i),
            'open': 10.0 + i, 'high': 12.0 + i, 'low': 9.0 + i, 'close': 11.0 + i, 'volume': 1000
        })
        
    manager.get_candles.return_value = bars
    return manager

def test_engine_insufficient_data(mock_db_manager):
    # Only return 1 bar
    mock_db_manager.get_candles.return_value = [{'symbol': 'SPY', 'timeframe': '1day', 'timestamp': datetime.datetime.now(), 'open': 10, 'high': 10, 'low': 10, 'close': 10, 'volume': 10}]
    
    engine = BacktestEngine(
        strategies={"dummy": DummyStrategy()},
        db_manager=mock_db_manager,
        symbol="SPY", timeframe="1day",
        start=datetime.datetime.now(), end=datetime.datetime.now(),
        lookback=1
    )
    
    with pytest.raises(ValueError, match="Insufficient data returned"):
        engine.run()

def test_engine_lookahead_bias_prevention(mock_db_manager):
    """
    Ensures that an order placed on bar N is filled at bar N+1's open price.
    """
    # Buy 10 shares on the very first actionable bar
    strategy = DummyStrategy(orders_to_emit=[[Order("SPY", OrderSide.BUY, 10)]])
    
    engine = BacktestEngine(
        strategies={"dummy": strategy},
        db_manager=mock_db_manager,
        symbol="SPY", timeframe="1day",
        start=datetime.datetime(2026, 1, 1), end=datetime.datetime(2026, 1, 5),
        lookback=1, # Need 1 bar of history, so first actionable bar is index 1
        initial_capital=1000.0,
        commission_pct=0.0
    )
    
    results = engine.run()
    res = results["dummy"]
    
    # 1 trade should have occurred
    assert len(res.trades) == 1
    trade = res.trades[0]
    
    # Bar index 0 (lookback): Date 1, Open 10, Close 11
    # Bar index 1 (1st actionable): Date 2, Open 11, Close 12  <-- Strategy sees this and says BUY
    # Bar index 2 (execution): Date 3, Open 12, Close 13       <-- Engine fills here
    
    assert trade.fill_price == 12.0
    assert trade.timestamp == datetime.datetime(2026, 1, 3, tzinfo=datetime.timezone.utc)

def test_engine_buy_and_hold_equity(mock_db_manager):
    strategy = DummyStrategy(orders_to_emit=[[Order("SPY", OrderSide.BUY, 100)]])
    
    engine = BacktestEngine(
        strategies={"dummy": strategy},
        db_manager=mock_db_manager,
        symbol="SPY", timeframe="1day",
        start=datetime.datetime(2026, 1, 1), end=datetime.datetime(2026, 1, 5),
        lookback=0, # First actionable bar is index 0
        initial_capital=2000.0,
        commission_pct=0.0
    )
    
    results = engine.run()
    res = results["dummy"]
    
    # Trade fills at Bar index 1 open = 11.0
    # Cost = 100 * 11.0 = 1100. Cash remaining = 900
    # Final Bar (index 4) close = 15.0
    # Position value = 100 * 15.0 = 1500
    # Final Equity = 900 + 1500 = 2400
    
    assert res.final_equity == 2400.0
    assert abs(res.total_return_pct - 20.0) < 1e-9  # using math.isclose logic for float comparison
    assert len(res.trades) == 1
