import pytest
import datetime
from unittest.mock import MagicMock

from db.manager import OHLCVManager
from db.connection import get_db_connection
from ingestion.engine import IngestionEngine
from ingestion.models import Bar

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Ensure the DB is clean before tests run."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE ohlcv;")
        conn.commit()
    yield

@pytest.fixture
def clean_db():
    """Clear DB before each test."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE ohlcv;")
        conn.commit()
    yield

@pytest.fixture
def manager():
    return OHLCVManager()

def test_ingestion_engine_full_fetch(manager, clean_db):
    """Test that a fresh request fetches and inserts everything."""
    mock_provider = MagicMock()
    
    start_ts = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    end_ts = datetime.datetime(2026, 1, 3, tzinfo=datetime.timezone.utc)
    
    # Provider will return 3 days of data
    mock_bars = [
        Bar("SPY", "1day", start_ts, 100, 105, 95, 102, 1000),
        Bar("SPY", "1day", start_ts + datetime.timedelta(days=1), 102, 106, 100, 105, 1100),
        Bar("SPY", "1day", end_ts, 105, 110, 104, 108, 1200),
    ]
    mock_provider.fetch_data.return_value = mock_bars
    
    engine = IngestionEngine(db_manager=manager, provider=mock_provider)
    engine.ingest("SPY", "1day", start_ts, end_ts)
    
    # Provider should be called once for the full range
    mock_provider.fetch_data.assert_called_once_with("SPY", "1day", start_ts, end_ts)
    
    # Data should be in DB
    db_data = manager.get_candles("SPY", "1day", start_ts, end_ts)
    assert len(db_data) == 3
    assert float(db_data[0]['close']) == 102.0

def test_ingestion_engine_skip_existing(manager, clean_db):
    """Test that requesting the exact same range skips the fetch."""
    mock_provider = MagicMock()
    
    start_ts = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    end_ts = datetime.datetime(2026, 1, 3, tzinfo=datetime.timezone.utc)
    
    # Pre-populate DB
    manager.insert_candles([
        {'symbol': 'SPY', 'timeframe': '1day', 'timestamp': start_ts, 'open': 1, 'high': 1, 'low': 1, 'close': 1, 'volume': 1},
        {'symbol': 'SPY', 'timeframe': '1day', 'timestamp': end_ts, 'open': 1, 'high': 1, 'low': 1, 'close': 1, 'volume': 1}
    ])
    
    engine = IngestionEngine(db_manager=manager, provider=mock_provider)
    engine.ingest("SPY", "1day", start_ts, end_ts)
    
    # Provider should NOT be called
    mock_provider.fetch_data.assert_not_called()

def test_ingestion_engine_partial_fetch(manager, clean_db):
    """Test requesting a range that partially overlaps existing data."""
    mock_provider = MagicMock()
    
    # We want Jan 1 to Jan 5
    req_start = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    req_end = datetime.datetime(2026, 1, 5, tzinfo=datetime.timezone.utc)
    
    # DB has Jan 2 to Jan 4
    db_start = datetime.datetime(2026, 1, 2, tzinfo=datetime.timezone.utc)
    db_end = datetime.datetime(2026, 1, 4, tzinfo=datetime.timezone.utc)
    
    manager.insert_candles([
        {'symbol': 'SPY', 'timeframe': '1day', 'timestamp': db_start, 'open': 1, 'high': 1, 'low': 1, 'close': 1, 'volume': 1},
        {'symbol': 'SPY', 'timeframe': '1day', 'timestamp': db_end, 'open': 1, 'high': 1, 'low': 1, 'close': 1, 'volume': 1}
    ])
    
    engine = IngestionEngine(db_manager=manager, provider=mock_provider)
    engine.ingest("SPY", "1day", req_start, req_end)
    
    # Provider should be called twice:
    # 1. Before DB data (Jan 1 to just before Jan 2)
    # 2. After DB data (Just after Jan 4 to Jan 5)
    assert mock_provider.fetch_data.call_count == 2
    
    calls = mock_provider.fetch_data.call_args_list
    
    call1_args, call1_kwargs = calls[0]
    assert call1_args[2] == req_start  # Jan 1
    assert call1_args[3] == db_start - datetime.timedelta(microseconds=1)  # Just before Jan 2
    
    call2_args, call2_kwargs = calls[1]
    assert call2_args[2] == db_end + datetime.timedelta(microseconds=1)  # Just after Jan 4
    assert call2_args[3] == req_end  # Jan 5
