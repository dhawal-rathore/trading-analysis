import os
import psycopg2
from psycopg2 import pool
from contextlib import contextmanager

# Get environment variables
POSTGRES_USER = os.environ.get("POSTGRES_USER", "trading_user")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "trading_secure_pass")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "trading_db")
DB_HOST = os.environ.get("DB_HOST", "db")
DB_PORT = os.environ.get("DB_PORT", "5432")

# Create a connection pool
try:
    connection_pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=20,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=POSTGRES_DB
    )
    if connection_pool:
        print("Connection pool created successfully")
except (Exception, psycopg2.DatabaseError) as error:
    print("Error while connecting to PostgreSQL", error)

@contextmanager
def get_db_connection():
    """
    Context manager to yield a database connection from the pool.
    Usage:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    """
    conn = None
    try:
        conn = connection_pool.getconn()
        yield conn
    finally:
        if conn:
            connection_pool.putconn(conn)
