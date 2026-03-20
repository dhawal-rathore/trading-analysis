import pytest
import datetime
from db.connection import get_db_connection
from db.manager import OHLCVManager

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """
    Ensure the test database is clean before running tests.
    Since we're running in docker-compose, the init.sql has already run.
    We just need to clear any existing data.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE ohlcv;")
        conn.commit()
    yield

@pytest.fixture
def clean_db():
    """
    Fixture to clear the database before a test.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE ohlcv;")
        conn.commit()
    yield

@pytest.fixture
def manager():
    return OHLCVManager()

@pytest.fixture
def base_time():
    # Use timezone-aware UTC datetime for timestamp consistency with PostgreSQL TIMESTAMPTZ
    return datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)
