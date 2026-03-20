import pytest
import datetime
from typing import List, Optional

from db.manager import OHLCVManager
from db.connection import get_db_connection
from backtesting.engine import BacktestEngine
from backtesting.strategy import Strategy
from backtesting.context import MarketContext
from backtesting.models import Order, OrderSide

# Clean DB setup
@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE ohlcv;")
        conn.commit()
    yield

@pytest.fixture
def clean_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE ohlcv;")
        conn.commit()
    yield

@pytest.fixture
def manager():
    return OHLCVManager()

class BuyAndHoldStrategy(Strategy):
    """Buys 10 shares on the very first bar and holds them."""
    def __init__(self):
        self.has_bought = False
        
    def on_bar(self, context: MarketContext) -> Optional[List[Order]]:
        if not self.has_bought:
            self.has_bought = True
            return [Order("SPY", OrderSide.BUY, 10)]
        return None

class DoNothingStrategy(Strategy):
    """A strategy that makes no trades."""
    def on_bar(self, context: MarketContext) -> Optional[List[Order]]:
        return None


def test_engine_integration_buy_and_hold(manager, clean_db):
    base_ts = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    
    # Pre-seed 5 days of data into DB
    records = []
    for i in range(5):
        records.append({
            'symbol': 'SPY', 'timeframe': '1day', 'timestamp': base_ts + datetime.timedelta(days=i),
            'open': 100 + i, 'high': 105 + i, 'low': 95 + i, 'close': 102 + i, 'volume': 1000
        })
    manager.insert_candles(records)

    engine = BacktestEngine(
        strategies={"dummy": BuyAndHoldStrategy()},
        db_manager=manager,
        symbol="SPY", timeframe="1day",
        start=base_ts, end=base_ts + datetime.timedelta(days=4),
        lookback=1,
        initial_capital=2000.0,
        commission_pct=0.0,
        flat_commission=0.0
    )
    
    results = engine.run()
    res = results["dummy"]
    
    # Assertions
    assert len(res.trades) == 1
    trade = res.trades[0]
    
    # Lookback=1 means index 1 is first actionable bar (Jan 2).
    # Order generated on Jan 2, filled on Jan 3 open.
    # Jan 3 (i=2) open = 100 + 2 = 102
    assert trade.fill_price == 102.0
    assert trade.timestamp == base_ts + datetime.timedelta(days=2)
    
    # Value calc:
    # Bought 10 shares at 102 = $1020 spent. Cash remaining = $980.
    # Final day (Jan 5) close price = 102 + 4 = 106.
    # Value of 10 shares = $1060.
    # Final equity = $980 + $1060 = $2040.
    assert res.final_equity == 2040.0
    assert res.total_return_pct == ((2040.0 / 2000.0) - 1) * 100.0

def test_engine_integration_do_nothing(manager, clean_db):
    base_ts = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    records = []
    for i in range(5):
        records.append({
            'symbol': 'SPY', 'timeframe': '1day', 'timestamp': base_ts + datetime.timedelta(days=i),
            'open': 100, 'high': 105, 'low': 95, 'close': 100, 'volume': 1000
        })
    manager.insert_candles(records)

    engine = BacktestEngine(
        strategies={"dummy": DoNothingStrategy()},
        db_manager=manager,
        symbol="SPY", timeframe="1day",
        start=base_ts, end=base_ts + datetime.timedelta(days=4),
        lookback=0,
        initial_capital=1000.0
    )
    
    results = engine.run()
    res = results["dummy"]
    
    assert len(res.trades) == 0
    assert res.final_equity == 1000.0
    assert res.total_return_pct == 0.0
