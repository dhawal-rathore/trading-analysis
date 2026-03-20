import datetime
from psycopg2.extras import execute_values, RealDictCursor
from .connection import get_db_connection

class OHLCVManager:
    """
    Data manager for OHLCV table.
    Provides methods to insert, query, and track OHLCV data.
    """
    
    def insert_candle(self, symbol: str, timeframe: str, timestamp: datetime.datetime, 
                      open_price: float, high_price: float, low_price: float, 
                      close_price: float, volume: float) -> None:
        """
        Upsert a single OHLCV candle.
        """
        query = """
            INSERT INTO ohlcv (symbol, timeframe, timestamp, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, timeframe, timestamp) 
            DO UPDATE SET 
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume;
        """
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (symbol, timeframe, timestamp, open_price, high_price, low_price, close_price, volume))
            conn.commit()

    def insert_candles(self, records: list[dict]) -> None:
        """
        Bulk upsert multiple OHLCV candles.
        Expected dict format:
        {'symbol': 'BTC', 'timeframe': '1hr', 'timestamp': dt, 'open': 100, 'high': 101, 'low': 99, 'close': 100, 'volume': 500}
        """
        if not records:
            return
            
        query = """
            INSERT INTO ohlcv (symbol, timeframe, timestamp, open, high, low, close, volume)
            VALUES %s
            ON CONFLICT (symbol, timeframe, timestamp) 
            DO UPDATE SET 
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume;
        """
        # Prepare a list of tuples for execute_values
        values = [
            (
                r['symbol'], r['timeframe'], r['timestamp'], 
                r['open'], r['high'], r['low'], r['close'], r['volume']
            )
            for r in records
        ]
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                execute_values(cur, query, values)
            conn.commit()

    def get_candles(self, symbol: str, timeframe: str, start: datetime.datetime, end: datetime.datetime) -> list[dict]:
        """
        Get candles for a specific symbol and timeframe within a time range (inclusive).
        """
        query = """
            SELECT symbol, timeframe, timestamp, open, high, low, close, volume
            FROM ohlcv
            WHERE symbol = %s AND timeframe = %s AND timestamp >= %s AND timestamp <= %s
            ORDER BY timestamp ASC;
        """
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (symbol, timeframe, start, end))
                # Convert RealDictRow to regular dict and numeric to float
                results = cur.fetchall()
                return [dict(r) for r in results]

    def get_candle(self, symbol: str, timeframe: str, timestamp: datetime.datetime) -> dict | None:
        """
        Get a specific candle by timestamp.
        """
        query = """
            SELECT symbol, timeframe, timestamp, open, high, low, close, volume
            FROM ohlcv
            WHERE symbol = %s AND timeframe = %s AND timestamp = %s;
        """
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (symbol, timeframe, timestamp))
                res = cur.fetchone()
                return dict(res) if res else None

    def has_data(self, symbol: str, timeframe: str, timestamp: datetime.datetime) -> bool:
        """
        Check if data exists for a specific timestamp.
        """
        query = """
            SELECT 1 FROM ohlcv
            WHERE symbol = %s AND timeframe = %s AND timestamp = %s;
        """
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (symbol, timeframe, timestamp))
                return cur.fetchone() is not None

    def get_data_range(self, symbol: str, timeframe: str) -> tuple[datetime.datetime, datetime.datetime] | None:
        """
        Get the minimum and maximum timestamp available for a given symbol and timeframe.
        Returns a tuple of (min_timestamp, max_timestamp) or None if no data.
        """
        query = """
            SELECT MIN(timestamp), MAX(timestamp)
            FROM ohlcv
            WHERE symbol = %s AND timeframe = %s;
        """
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (symbol, timeframe))
                res = cur.fetchone()
                if res and res[0] is not None:
                    return res
                return None

    def get_missing_timestamps(self, symbol: str, timeframe: str, expected_timestamps: list[datetime.datetime]) -> list[datetime.datetime]:
        """
        Given a list of expected timestamps, return a list of timestamps that are missing in the database.
        """
        if not expected_timestamps:
            return []
            
        min_ts = min(expected_timestamps)
        max_ts = max(expected_timestamps)
        
        query = """
            SELECT timestamp FROM ohlcv
            WHERE symbol = %s AND timeframe = %s AND timestamp >= %s AND timestamp <= %s;
        """
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (symbol, timeframe, min_ts, max_ts))
                existing_timestamps = {row[0] for row in cur.fetchall()}
                
        return [ts for ts in expected_timestamps if ts not in existing_timestamps]

    def delete_candles(self, symbol: str, timeframe: str, start: datetime.datetime, end: datetime.datetime) -> int:
        """
        Delete candles within a given time range. Returns the number of deleted rows.
        """
        query = """
            DELETE FROM ohlcv
            WHERE symbol = %s AND timeframe = %s AND timestamp >= %s AND timestamp <= %s;
        """
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (symbol, timeframe, start, end))
                deleted_count = cur.rowcount
            conn.commit()
            return deleted_count
