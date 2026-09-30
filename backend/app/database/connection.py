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
            purity REAL NOT NULL,
            tick_size REAL NOT NULL,
            lot_size_description TEXT,
            expiry_rule TEXT,
            tender_period_days INTEGER DEFAULT 3,
            delivery_unit TEXT,
            official_source_url TEXT,
            audit_date TEXT,
            active INTEGER DEFAULT 1
        );
        """)

        # Add columns if upgrading from earlier schema
        for col_name, col_type in [
            ("expiry_rule", "TEXT"),
            ("tender_period_days", "INTEGER DEFAULT 3"),
            ("delivery_unit", "TEXT"),
            ("official_source_url", "TEXT"),
            ("audit_date", "TEXT")
        ]:
            try:
                cursor.execute(f"ALTER TABLE contracts ADD COLUMN {col_name} {col_type};")
            except sqlite3.OperationalError:
                pass  # column already exists

        # Insert/Update default contract specs
        for spec in CONTRACT_SPECS.values():
            cursor.execute("""
            INSERT INTO contracts (
                symbol, name, trading_unit_grams, quote_unit_grams,
                multiplier_to_10g, purity, tick_size, lot_size_description,
                expiry_rule, tender_period_days, delivery_unit, official_source_url, audit_date, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(symbol) DO UPDATE SET
                name=excluded.name,
                trading_unit_grams=excluded.trading_unit_grams,
                quote_unit_grams=excluded.quote_unit_grams,
                multiplier_to_10g=excluded.multiplier_to_10g,
                purity=excluded.purity,
                tick_size=excluded.tick_size,
                lot_size_description=excluded.lot_size_description,
                expiry_rule=excluded.expiry_rule,
                tender_period_days=excluded.tender_period_days,
                delivery_unit=excluded.delivery_unit,
                official_source_url=excluded.official_source_url,
                audit_date=excluded.audit_date;
            """, (
                spec.symbol, spec.name, spec.trading_unit_grams, spec.quote_unit_grams,
                spec.multiplier_to_10g, spec.purity, spec.tick_size, spec.lot_size_description,
                spec.expiry_rule, spec.tender_period_days, spec.delivery_unit, spec.official_source_url, spec.audit_date
            ))

        # Market data table for daily bhavcopy bars
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            trade_date TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
