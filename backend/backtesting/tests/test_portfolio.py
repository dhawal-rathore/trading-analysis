import pytest
import datetime

from backtesting.models import Order, OrderSide
from backtesting.portfolio import Portfolio

def test_portfolio_initial_state():
    p = Portfolio(10000.0)
    assert p.cash == 10000.0
    assert len(p.positions) == 0
    assert p.equity({}) == 10000.0

def test_portfolio_buy_success():
    p = Portfolio(10000.0)
    ts = datetime.datetime.now()
    order = Order("SPY", OrderSide.BUY, 10)
    
    trade = p.execute_order(order, fill_price=100.0, timestamp=ts, commission_pct=0.0)
    
    assert p.cash == 9000.0
    assert p.positions["SPY"] == 10
    assert trade.quantity == 10
    assert trade.commission == 0.0

def test_portfolio_buy_with_commission():
    p = Portfolio(10000.0)
    ts = datetime.datetime.now()
    order = Order("SPY", OrderSide.BUY, 10)
    
    # 1% commission = 10 * 100 * 0.01 = $10 + $1 flat = $11
    trade = p.execute_order(order, fill_price=100.0, timestamp=ts, commission_pct=0.01, flat_commission=1.0)
    
    assert p.cash == 8989.0  # 10000 - 1000 - 11
    assert p.positions["SPY"] == 10

def test_portfolio_insufficient_funds():
    p = Portfolio(500.0)
    ts = datetime.datetime.now()
    order = Order("SPY", OrderSide.BUY, 10)
    
    with pytest.raises(ValueError, match="Insufficient funds"):
        p.execute_order(order, fill_price=100.0, timestamp=ts)

def test_portfolio_sell_success():
    p = Portfolio(10000.0)
    ts = datetime.datetime.now()
    
    # Buy first
    p.execute_order(Order("SPY", OrderSide.BUY, 10), fill_price=100.0, timestamp=ts)
    assert p.cash == 9000.0
    
    # Sell half
    p.execute_order(Order("SPY", OrderSide.SELL, 5), fill_price=150.0, timestamp=ts)
    assert p.cash == 9750.0  # 9000 + (5 * 150)
    assert p.positions["SPY"] == 5

def test_portfolio_no_short_selling():
    p = Portfolio(10000.0)
    ts = datetime.datetime.now()
    
    with pytest.raises(ValueError, match="Cannot short sell"):
        p.execute_order(Order("SPY", OrderSide.SELL, 10), fill_price=100.0, timestamp=ts)

def test_portfolio_equity():
    p = Portfolio(10000.0)
    ts = datetime.datetime.now()
    
    p.execute_order(Order("AAPL", OrderSide.BUY, 10), fill_price=150.0, timestamp=ts)
    assert p.cash == 8500.0
    
    # Price drops to 100
    assert p.equity({"AAPL": 100.0}) == 9500.0  # 8500 + 1000
    
    # Price rises to 200
    assert p.equity({"AAPL": 200.0}) == 10500.0 # 8500 + 2000
