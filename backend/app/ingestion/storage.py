"""
AurumIQ Bhavcopy Database Persistence
Stores raw imported records, import audit sessions, and validation diagnostic logs in SQLite.
"""
import json
from typing import Dict, Any, List
from app.database.connection import get_db

def save_bhavcopy_import_audit(
    parse_result: Dict[str, Any],
    source: str
) -> int:
    """
    Persists raw import metadata, raw row records, and validation logs into SQLite.
    Returns the created import_id.
    """
    req_date = parse_result.get("requested_date")
    act_date = parse_result.get("actual_data_date")
    status = parse_result.get("status", "UNKNOWN")
    error_msg = parse_result.get("message", "")
    
    val_report = parse_result.get("validation_report") or {}
    total_found = val_report.get("total_extracted", 0)
    valid_count = val_report.get("valid_count", 0)
    rejected_count = val_report.get("rejected_count", 0)
    duplicate_count = val_report.get("duplicate_count", 0)

    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Insert into raw_bhavcopy_imports
        cursor.execute("""
            INSERT INTO raw_bhavcopy_imports (
                source, requested_date, actual_data_date, status,
                total_rows_found, valid_rows_count, rejected_rows_count,
                duplicate_rows_count, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            source, req_date, act_date, status,
            total_found, valid_count, rejected_count, duplicate_count, error_msg
        ))
        import_id = cursor.lastrowid

        # 2. Insert into raw_bhavcopy_records
        raw_records = parse_result.get("raw_records", [])
        for r in raw_records:
            cursor.execute("""
                INSERT INTO raw_bhavcopy_records (
                    import_id, raw_symbol, clean_symbol, raw_trade_date,
                    clean_trade_date, raw_expiry_date, clean_expiry_date,
                    contract_id, open, high, low, close, volume, open_interest,
                    is_valid, validation_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                import_id,
                r.get("raw_symbol"), r.get("clean_symbol"),
                r.get("raw_trade_date"), r.get("clean_trade_date"),
                r.get("raw_expiry_date"), r.get("clean_expiry_date"),
                r.get("contract_id"),
                r.get("open"), r.get("high"), r.get("low"), r.get("close"),
                r.get("volume", 0), r.get("open_interest", 0),
                r.get("is_valid", 1), r.get("validation_error")
            ))

        # 3. Insert rejections into validation_logs
        rejected_samples = val_report.get("rejected_samples", [])
        for rej in rejected_samples:
            row_idx = rej.get("row_index", -1)
            reason = rej.get("reason", "Validation failure")
            raw_data = json.dumps(rej.get("raw", {}))
            cursor.execute("""
                INSERT INTO validation_logs (
                    import_id, row_index, raw_data_json, reason, severity
                ) VALUES (?, ?, ?, ?, 'ERROR');
            """, (import_id, row_idx, raw_data, reason))

        # 4. If import was successful and valid records exist, insert into market_data
        if parse_result.get("success") and parse_result.get("records"):
            market_records = parse_result["records"]
            cursor.executemany("""
                INSERT INTO market_data (
                    symbol, trade_date, expiry_date, open, high, low, close,
                    volume, open_interest, normalized_close_10g, purity_adjusted_10g,
                    dte, implied_basis_pct
                ) VALUES (
                    :symbol, :trade_date, :expiry_date, :open, :high, :low, :close,
                    :volume, :open_interest, :normalized_close_10g, :purity_adjusted_10g,
                    :dte, :implied_basis_pct
                ) ON CONFLICT(symbol, trade_date, expiry_date) DO UPDATE SET
                    open=excluded.open,
                    high=excluded.high,
                    low=excluded.low,
                    close=excluded.close,
                    volume=excluded.volume,
                    open_interest=excluded.open_interest,
                    normalized_close_10g=excluded.normalized_close_10g,
                    purity_adjusted_10g=excluded.purity_adjusted_10g,
                    dte=excluded.dte,
                    implied_basis_pct=excluded.implied_basis_pct;
            """, market_records)
            
            # Log into legacy ingestion_logs for backward compatibility
            dates = [m["trade_date"] for m in market_records]
            cursor.execute("""
                INSERT INTO ingestion_logs (
                    source, records_ingested, trade_date_start, trade_date_end, status
                ) VALUES (?, ?, ?, ?, ?);
            """, (source, len(market_records), min(dates), max(dates), "SUCCESS"))

    return import_id

def get_recent_bhavcopy_imports(limit: int = 15) -> List[Dict[str, Any]]:
    """Returns recent bhavcopy import sessions with audit statistics."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, source, requested_date, actual_data_date, status,
                   total_rows_found, valid_rows_count, rejected_rows_count,
                   duplicate_rows_count, error_message, created_at
            FROM raw_bhavcopy_imports
            ORDER BY id DESC
            LIMIT ?;
        """, (limit,))
        return [dict(r) for r in cursor.fetchall()]
