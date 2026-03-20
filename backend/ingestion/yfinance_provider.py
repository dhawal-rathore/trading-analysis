import datetime
import logging
from typing import List

import yfinance as yf
import pandas as pd

from .base import Ingester
from .models import Bar

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YFinanceIngester(Ingester):
    """
    Ingester implementation for Yahoo Finance (yfinance).
    """

    # Map our generic DB timeframes to yfinance interval strings
    TIMEFRAME_MAP = {
        '1min': '1m',
        '5min': '5m',
        '15min': '15m',
        '30min': '30m',
        '1hr': '1h',
        '1day': '1d',
        '1wk': '1wk',
        '1mo': '1mo'
    }

    def fetch_data(self, symbol: str, timeframe: str, start: datetime.datetime, end: datetime.datetime) -> List[Bar]:
        if timeframe not in self.TIMEFRAME_MAP:
            logger.error(f"Unsupported timeframe '{timeframe}' for YFinance.")
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        yf_interval = self.TIMEFRAME_MAP[timeframe]
        
        # yfinance download expects naive strings or standard dates; it returns timezone-aware info generally
        # We'll adjust `start` and `end` if they are timezone-aware to ensure safe querying.
        
        logger.info(f"Fetching {symbol} data from YFinance for interval {yf_interval} "
                    f"from {start.strftime('%Y-%m-%d %H:%M:%S')} to {end.strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            # yfinance upper bound is exclusive, so we add a little buffer to ensure the 'end' candle is included if it falls exactly on the bound.
            fetch_end = end + datetime.timedelta(days=1) if 'd' in yf_interval or 'wk' in yf_interval else end + datetime.timedelta(hours=1)
            
            df = yf.download(
                tickers=symbol,
                start=start,
                end=fetch_end,
                interval=yf_interval,
                progress=False
            )
            
            if df.empty:
                logger.warning(f"No data returned from YFinance for {symbol} ({start} to {end}).")
                return []

            # yfinance returns multi-index columns in recent versions for single symbols, or single index.
            # Flatten the columns if necessary to avoid `df['Open'].iloc[0]` being a Series
            if isinstance(df.columns, pd.MultiIndex):
                # Typically, level 0 is 'Price', level 1 is 'Ticker'. We just want 'Price'.
                df.columns = df.columns.get_level_values(0)

            bars = []
            for index, row in df.iterrows():
                # yfinance index (Date/Datetime) is often tz-aware (e.g. America/New_York)
                # We normalize to UTC to match our postgres TIMESTAMPTZ design
                ts = index
                if ts.tzinfo is None:
                    # If naive, assume UTC for safety or localize then convert. YF usually returns local.
                    # We'll just set to UTC.
                    ts = ts.tz_localize('UTC')
                else:
                    ts = ts.tz_convert('UTC')
                
                # Check bounds since we padded the end date
                if not (start <= ts <= end):
                    continue

                bar = Bar(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=ts.to_pydatetime(),
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=float(row['Volume'])
                )
                bars.append(bar)

            logger.info(f"Successfully fetched {len(bars)} bars for {symbol}.")
            return bars

        except Exception as e:
            logger.error(f"Error fetching data from YFinance for {symbol}: {e}")
            return []
