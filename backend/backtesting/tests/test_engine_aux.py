import pytest
import datetime
from unittest.mock import MagicMock

from backtesting.engine import BacktestEngine
from backtesting.models import Order, OrderSide
from backtesting.strategy import Strategy

class DummyStrategy(Strategy):
    def __init__(self, orders_to_emit=None):
        self.orders_to_emit = orders_to_emit or []
        self.bar_count = 0
        
    def on_bar(self, context):
        orders = self.orders_to_emit[self.bar_count] if self.bar_count < len(self.orders_to_emit) else None
        self.bar_count += 1
        return orders

@pytest.fixture
def mock_db_manager_aux():
    manager = MagicMock()
    
    # Create master data: 3 days of 1day bars
    base_ts = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    master_bars = []
    for i in range(3):
        master_bars.append({
            'symbol': 'SPY', 'timeframe': '1day', 'timestamp': base_ts + datetime.timedelta(days=i),
            'open': 100.0 + i*10, 'high': 105.0 + i*10, 'low': 95.0 + i*10, 'close': 102.0 + i*10, 'volume': 1000
        })
        
    # Create auxiliary data for AAPL
    # AAPL bars will be roughly at the same days but offset by some hours, or just daily bars too
    # Let's say we get a signal on SPY at end of day 0 (timestamp 2026-01-01). 
    # The order for AAPL should fill on the first AAPL bar strictly after 2026-01-01.
    aux_bars_aapl = [
        {
            'symbol': 'AAPL', 'timeframe': '1hr', 'timestamp': base_ts + datetime.timedelta(hours=2),
            'open': 50.0, 'high': 52.0, 'low': 49.0, 'close': 51.0, 'volume': 100
        },
        {
            # This is strictly after day 0 (2026-01-01 00:00). So a signal at 2026-01-01 should fill here!
            'symbol': 'AAPL', 'timeframe': '1hr', 'timestamp': base_ts + datetime.timedelta(days=1, hours=1),
            'open': 55.0, 'high': 56.0, 'low': 54.0, 'close': 55.5, 'volume': 100
        },
        {
            'symbol': 'AAPL', 'timeframe': '1hr', 'timestamp': base_ts + datetime.timedelta(days=2, hours=1),
            'open': 60.0, 'high': 62.0, 'low': 59.0, 'close': 61.0, 'volume': 100
        }
    ]
    
    def side_effect(symbol, timeframe, start, end):
        if symbol == 'SPY':
            return master_bars
        elif symbol == 'AAPL':
            return aux_bars_aapl
        return []
        
    manager.get_candles.side_effect = side_effect
    return manager

def test_engine_auxiliary_fill(mock_db_manager_aux):
    # Buy 10 AAPL shares on the very first actionable bar (SPY index 0)
    strategy = DummyStrategy(orders_to_emit=[[Order("AAPL", OrderSide.BUY, 10)]])
    
    engine = BacktestEngine(
        strategies={"dummy": strategy},
        db_manager=mock_db_manager_aux,
        symbol="SPY", timeframe="1day",
        start=datetime.datetime(2026, 1, 1), end=datetime.datetime(2026, 1, 5),
        lookback=0, 
        initial_capital=1000.0,
        commission_pct=0.0,
        auxiliary_series=[("AAPL", "1hr")]
    )
    
    results = engine.run()
    res = results["dummy"]
    
    # 1 trade should have occurred
    assert len(res.trades) == 1
    trade = res.trades[0]
    
    # Engine processes SPY index 0 (2026-01-01 00:00:00). Strategy emits BUY AAPL.
    # Fill boundary is 2026-01-01 00:00:00.
    # Aux data for AAPL has bars at:
    # 1. 2026-01-01 02:00:00 (Open: 50.0) -> This is strictly after the boundary! So it should fill here.
    
    assert trade.symbol == "AAPL"
    assert trade.fill_price == 50.0
    assert trade.timestamp == datetime.datetime(2026, 1, 1, 2, tzinfo=datetime.timezone.utc)
    
    # Final equity check
    # Initial capital = 1000. 
    # Bought 10 AAPL @ 50.0 = 500. Cash remaining = 500.
    # Last AAPL close price <= final master bar (2026-01-03 00:00) 
    # AAPL bar 3 is at 2026-01-03 01:00 (after final master bar!). 
    # Wait, AAPL bar 2 is 2026-01-02 01:00 (Close: 55.5). This is <= final master bar (2026-01-03).
    # So AAPL price should be 55.5.
    # Equity = 500 (cash) + 10 * 55.5 = 1055.0
    assert res.final_equity == 1055.0

def test_engine_auxiliary_fill_mtm_spy(mock_db_manager_aux):
    # What if we trade SPY, but also have SPY aux data?
    # According to our design, if SPY is in aux data, we should use the aux data for filling SPY.
    # Let's mock a scenario where SPY has both 1day and 1hr data
    manager = MagicMock()
    
    base_ts = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    master_bars = [
        {'symbol': 'SPY', 'timeframe': '1day', 'timestamp': base_ts, 'open': 100, 'high': 110, 'low': 90, 'close': 105, 'volume': 1000},
        {'symbol': 'SPY', 'timeframe': '1day', 'timestamp': base_ts + datetime.timedelta(days=1), 'open': 110, 'high': 120, 'low': 100, 'close': 115, 'volume': 1000}
    ]
    
    aux_bars = [
        {'symbol': 'SPY', 'timeframe': '1hr', 'timestamp': base_ts + datetime.timedelta(hours=1), 'open': 101, 'high': 102, 'low': 100, 'close': 101.5, 'volume': 100},
        {'symbol': 'SPY', 'timeframe': '1hr', 'timestamp': base_ts + datetime.timedelta(days=1, hours=1), 'open': 111, 'high': 112, 'low': 110, 'close': 111.5, 'volume': 100}
    ]
    
    def side_effect(symbol, timeframe, start, end):
        if timeframe == '1day': return master_bars
        if timeframe == '1hr': return aux_bars
        return []
        
    manager.get_candles.side_effect = side_effect

    strategy = DummyStrategy(orders_to_emit=[[Order("SPY", OrderSide.BUY, 10)]])
    
    engine = BacktestEngine(
        strategies={"dummy": strategy},
        db_manager=manager,
        symbol="SPY", timeframe="1day",
        start=datetime.datetime(2026, 1, 1), end=datetime.datetime(2026, 1, 5),
        lookback=0, 
        initial_capital=2000.0,
        commission_pct=0.0,
        auxiliary_series=[("SPY", "1hr")]
    )
    
    results = engine.run()
    res = results["dummy"]
    
    assert len(res.trades) == 1
    trade = res.trades[0]
    
    # Boundary is 2026-01-01 00:00:00. Next SPY 1hr is 2026-01-01 01:00:00 with Open=101.
    assert trade.fill_price == 101.0
    assert trade.timestamp == datetime.datetime(2026, 1, 1, 1, tzinfo=datetime.timezone.utc)
    
    # Final equity:
    # Final master bar is index 1: 2026-01-02 00:00:00
    # Last SPY 1hr before or at 2026-01-02 00:00 is 2026-01-01 01:00 (Close=101.5).
    # (The next aux bar is 2026-01-02 01:00, which is > 2026-01-02 00:00)
    # Cash = 2000 - 10 * 101 = 990
    # Position = 10 * 101.5 = 1015
    # Total = 2005
    assert res.final_equity == 2005.0
