import datetime
from decimal import Decimal
from db.manager import OHLCVManager

def test_insert_and_get_candle(manager: OHLCVManager, clean_db, base_time):
    # Insert single candle
    manager.insert_candle(
        symbol="BTC", timeframe="1hr", timestamp=base_time,
        open_price=100.0, high_price=105.0, low_price=95.0, close_price=102.0, volume=500.5
    )
    
    # Retrieve it
    candle = manager.get_candle(symbol="BTC", timeframe="1hr", timestamp=base_time)
    
    assert candle is not None
    assert candle["symbol"] == "BTC"
    assert candle["timeframe"] == "1hr"
    assert candle["timestamp"] == base_time
    # Values might be returned as Decimal from psycopg2 RealDictCursor
    assert float(candle["open"]) == 100.0
    assert float(candle["high"]) == 105.0
    assert float(candle["low"]) == 95.0
    assert float(candle["close"]) == 102.0
    assert float(candle["volume"]) == 500.5

def test_insert_candles_bulk_and_get_candles(manager: OHLCVManager, clean_db, base_time):
    records = []
    for i in range(5):
        ts = base_time + datetime.timedelta(hours=i)
        records.append({
            "symbol": "ETH", "timeframe": "1hr", "timestamp": ts,
            "open": 2000 + i, "high": 2010 + i, "low": 1990 + i, "close": 2005 + i, "volume": 100
        })
        
    manager.insert_candles(records)
    
    # Query range
    end_time = base_time + datetime.timedelta(hours=4)
    results = manager.get_candles("ETH", "1hr", base_time, end_time)
    
    assert len(results) == 5
    # Verify order (should be ASC by timestamp)
    assert results[0]["timestamp"] == base_time
    assert results[-1]["timestamp"] == end_time

def test_has_data(manager: OHLCVManager, clean_db, base_time):
    assert manager.has_data("SOL", "1hr", base_time) is False
    
    manager.insert_candle(
        symbol="SOL", timeframe="1hr", timestamp=base_time,
        open_price=10, high_price=11, low_price=9, close_price=10, volume=100
    )
    
    assert manager.has_data("SOL", "1hr", base_time) is True
    assert manager.has_data("SOL", "1day", base_time) is False # Different timeframe

def test_upsert_idempotency(manager: OHLCVManager, clean_db, base_time):
    # Insert initially
    manager.insert_candle(
        symbol="BTC", timeframe="1hr", timestamp=base_time,
        open_price=100, high_price=110, low_price=90, close_price=100, volume=500
    )
    
    # Update with new values
    manager.insert_candle(
        symbol="BTC", timeframe="1hr", timestamp=base_time,
        open_price=100, high_price=110, low_price=90, close_price=105, volume=600 # Changed close and volume
    )
    
    candle = manager.get_candle("BTC", "1hr", base_time)
    assert float(candle["close"]) == 105.0
    assert float(candle["volume"]) == 600.0
    
    # Bulk upsert idempotency
    records = [{
        "symbol": "BTC", "timeframe": "1hr", "timestamp": base_time,
        "open": 100, "high": 110, "low": 90, "close": 108, "volume": 700
    }]
    manager.insert_candles(records)
    
    candle = manager.get_candle("BTC", "1hr", base_time)
    assert float(candle["close"]) == 108.0
    assert float(candle["volume"]) == 700.0

def test_get_data_range(manager: OHLCVManager, clean_db, base_time):
    assert manager.get_data_range("XRP", "1hr") is None
    
    manager.insert_candle("XRP", "1hr", base_time, 1, 1, 1, 1, 1)
    manager.insert_candle("XRP", "1hr", base_time + datetime.timedelta(hours=5), 1, 1, 1, 1, 1)
    manager.insert_candle("XRP", "1hr", base_time + datetime.timedelta(hours=2), 1, 1, 1, 1, 1)
    
    min_ts, max_ts = manager.get_data_range("XRP", "1hr")
    assert min_ts == base_time
    assert max_ts == base_time + datetime.timedelta(hours=5)

def test_get_missing_timestamps(manager: OHLCVManager, clean_db, base_time):
    # Insert 0, 1, 2, 4 (missing 3)
    for i in [0, 1, 2, 4]:
        ts = base_time + datetime.timedelta(hours=i)
        manager.insert_candle("DOGE", "1hr", ts, 0.1, 0.1, 0.1, 0.1, 1000)
        
    expected = [base_time + datetime.timedelta(hours=i) for i in range(5)]
    missing = manager.get_missing_timestamps("DOGE", "1hr", expected)
    
    assert len(missing) == 1
    assert missing[0] == base_time + datetime.timedelta(hours=3)

def test_delete_candles(manager: OHLCVManager, clean_db, base_time):
    records = []
    for i in range(5):
        ts = base_time + datetime.timedelta(hours=i)
        records.append({
            "symbol": "ETH", "timeframe": "1hr", "timestamp": ts,
            "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1
        })
    manager.insert_candles(records)
    
    # Delete hours 1 to 3
    start = base_time + datetime.timedelta(hours=1)
    end = base_time + datetime.timedelta(hours=3)
    
    deleted = manager.delete_candles("ETH", "1hr", start, end)
    assert deleted == 3
    
    # Verify remaining
    remaining = manager.get_candles("ETH", "1hr", base_time, base_time + datetime.timedelta(hours=5))
    assert len(remaining) == 2
    assert remaining[0]["timestamp"] == base_time
    assert remaining[1]["timestamp"] == base_time + datetime.timedelta(hours=4)

def test_multiple_timeframes(manager: OHLCVManager, clean_db, base_time):
    # Insert 1hr and 1day for same timestamp
    manager.insert_candle("BTC", "1hr", base_time, 1, 1, 1, 1, 1)
    manager.insert_candle("BTC", "1day", base_time, 2, 2, 2, 2, 2)
    
    candle_1hr = manager.get_candle("BTC", "1hr", base_time)
    candle_1day = manager.get_candle("BTC", "1day", base_time)
    
    assert float(candle_1hr["open"]) == 1.0
    assert float(candle_1day["open"]) == 2.0
