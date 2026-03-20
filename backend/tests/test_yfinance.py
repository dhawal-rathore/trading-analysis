import pytest
from unittest.mock import patch
import pandas as pd
import datetime

from ingestion.yfinance_provider import YFinanceIngester
from ingestion.models import Bar

@pytest.fixture
def dummy_yf_data():
    """Returns a dummy pandas DataFrame mimicking yfinance download output."""
    # Create tz-aware dates to mimic yfinance behavior (often local time, we'll use America/New_York)
    dates = pd.date_range(start="2026-01-01", periods=3, freq="D", tz="UTC")
    data = {
        'Open': [100.0, 102.0, 101.0],
        'High': [105.0, 106.0, 104.0],
        'Low': [99.0, 100.0, 98.0],
        'Close': [103.0, 101.0, 102.0],
        'Volume': [1000, 1500, 1200]
    }
    return pd.DataFrame(data, index=dates)

@pytest.fixture
def empty_yf_data():
    return pd.DataFrame()

def test_yfinance_ingester_fetch_data_success(dummy_yf_data):
    ingester = YFinanceIngester()
    
    start_date = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    end_date = datetime.datetime(2026, 1, 3, tzinfo=datetime.timezone.utc)
    
    with patch('yfinance.download', return_value=dummy_yf_data) as mock_download:
        bars = ingester.fetch_data("SPY", "1day", start_date, end_date)
        
        # Verify the download call
        mock_download.assert_called_once()
        args, kwargs = mock_download.call_args
        assert kwargs['tickers'] == "SPY"
        assert kwargs['interval'] == "1d"  # mapped from '1day'
        
        # Verify parsing
        assert len(bars) == 3
        assert all(isinstance(b, Bar) for b in bars)
        
        # Verify specific values of the first bar
        assert bars[0].symbol == "SPY"
        assert bars[0].timeframe == "1day"
        assert bars[0].open == 100.0
        assert bars[0].close == 103.0
        assert bars[0].volume == 1000
        # Timezone conversion check: should be converted to UTC
        assert bars[0].timestamp.tzinfo == datetime.timezone.utc

def test_yfinance_ingester_fetch_data_empty(empty_yf_data):
    ingester = YFinanceIngester()
    
    start_date = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    end_date = datetime.datetime(2026, 1, 3, tzinfo=datetime.timezone.utc)
    
    with patch('yfinance.download', return_value=empty_yf_data):
        bars = ingester.fetch_data("SPY", "1day", start_date, end_date)
        assert len(bars) == 0

def test_yfinance_ingester_unsupported_timeframe():
    ingester = YFinanceIngester()
    
    start_date = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    end_date = datetime.datetime(2026, 1, 3, tzinfo=datetime.timezone.utc)
    
    with pytest.raises(ValueError, match="Unsupported timeframe: 2day"):
        ingester.fetch_data("SPY", "2day", start_date, end_date)
