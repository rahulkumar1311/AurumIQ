"""
SQLite Database Connection and Schema Management for AurumIQ
"""
import sqlite3
from typing import Generator
from contextlib import contextmanager
from app.config import DB_PATH, CONTRACT_SPECS

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for high concurrent read/write performance
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db() -> None:
    """Initialize database tables and indexes."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Contracts metadata table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS contracts (
            symbol TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            trading_unit_grams REAL NOT NULL,
            quote_unit_grams REAL NOT NULL,
            multiplier_to_10g REAL NOT NULL,
