import datetime
import logging
from typing import List

from db.manager import OHLCVManager
from .base import Ingester

logger = logging.getLogger(__name__)

class IngestionEngine:
    """
    Orchestrates the fetching of data from a provider and storing it into the database.
    It minimizes network calls by querying the database for existing data ranges
    and only fetching what is strictly missing.
    """

    def __init__(self, db_manager: OHLCVManager, provider: Ingester):
        self.db_manager = db_manager
        self.provider = provider

    def ingest(self, symbol: str, timeframe: str, start: datetime.datetime, end: datetime.datetime) -> None:
        """
        Ingests data for the given symbol and timeframe from start to end.
        Skips data that is already present in the database.
        """
        # Ensure timezone-aware bounds (UTC)
        if start.tzinfo is None:
            start = start.replace(tzinfo=datetime.timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=datetime.timezone.utc)

        logger.info(f"Ingestion requested for {symbol} ({timeframe}) from {start} to {end}")

        # 1. Ask DB for existing data range
        existing_range = self.db_manager.get_data_range(symbol, timeframe)
        
        ranges_to_fetch = []

        if existing_range is None:
            # DB has absolutely no data for this symbol/timeframe
            logger.info("No existing data found in DB. Fetching full requested range.")
            ranges_to_fetch.append((start, end))
        else:
            db_min_ts, db_max_ts = existing_range
            
            # 2. Compute missing sub-ranges
            # Case A: Requested range is completely before existing data
            if end < db_min_ts:
                ranges_to_fetch.append((start, end))
                
            # Case B: Requested range is completely after existing data
            elif start > db_max_ts:
                ranges_to_fetch.append((start, end))
                
            # Case C: Requested range overlaps with existing data
            else:
                # Check for gap BEFORE existing data
                if start < db_min_ts:
                    ranges_to_fetch.append((start, db_min_ts - datetime.timedelta(microseconds=1)))
                
                # Check for gap AFTER existing data
                if end > db_max_ts:
                    ranges_to_fetch.append((db_max_ts + datetime.timedelta(microseconds=1), end))

        if not ranges_to_fetch:
            logger.info(f"Data for {symbol} ({timeframe}) between {start} and {end} already fully exists in DB. Skipping fetch.")
            return

        # 3. Call self.provider.fetch_data() on missing ranges
        for fetch_start, fetch_end in ranges_to_fetch:
            logger.info(f"Provider fetching missing gap: {fetch_start} to {fetch_end}")
            bars = self.provider.fetch_data(symbol, timeframe, fetch_start, fetch_end)
            
            if not bars:
                logger.warning(f"Provider returned no data for gap {fetch_start} to {fetch_end}")
                continue
                
            # 4. Insert fetched Bars using db_manager.insert_candles()
            records = [
                {
                    'symbol': b.symbol,
                    'timeframe': b.timeframe,
                    'timestamp': b.timestamp,
                    'open': b.open,
                    'high': b.high,
                    'low': b.low,
                    'close': b.close,
                    'volume': b.volume
                }
                for b in bars
            ]
            
            self.db_manager.insert_candles(records)
            logger.info(f"Inserted {len(records)} candles into database.")
