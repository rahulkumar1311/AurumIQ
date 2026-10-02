"""
AurumIQ MCX Bhavcopy Ingestion Module Automated Tests
Tests date formats, compact expiry parsing, symbol padding, duplicate records,
incorrect returned dates rejection, and SQLite audit persistence.
"""
import pytest
from datetime import datetime
from app.ingestion.mcx_parser import (
    parse_requested_date,
    check_trading_day,
    parse_compact_expiry_date,
    parse_trading_date,
    parse_mcx_bhavcopy_file
)
from app.ingestion.storage import save_bhavcopy_import_audit, get_recent_bhavcopy_imports
from app.database.connection import init_db, get_db

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

# 1. Date Formats (DD/MM/YYYY requested date validation)
def test_parse_requested_date_valid():
    dt, iso = parse_requested_date("15/09/2026")
    assert iso == "2026-09-15"
    assert dt.day == 15
    assert dt.month == 9
    assert dt.year == 2026

def test_parse_requested_date_invalid():
    with pytest.raises(ValueError) as exc:
        parse_requested_date("2026-99-99")
    assert "Invalid requested date format" in str(exc.value)

def test_weekend_detection():
    # 2026-10-03 is Saturday, 2026-10-04 is Sunday, 2026-10-05 is Monday
    sat = datetime(2026, 10, 3)
    sun = datetime(2026, 10, 4)
    mon = datetime(2026, 10, 5)

    is_sat, msg_sat = check_trading_day(sat)
    assert not is_sat
    assert "Saturday" in msg_sat

    is_sun, msg_sun = check_trading_day(sun)
    assert not is_sun
    assert "Sunday" in msg_sun

    is_mon, msg_mon = check_trading_day(mon)
    assert is_mon
    assert msg_mon == ""

# 2. Compact Expiry Parsing (e.g. 04SEP2026)
def test_compact_expiry_parsing():
    assert parse_compact_expiry_date("04SEP2026") == "2026-09-04"
    assert parse_compact_expiry_date("05NOV2024") == "2024-11-05"
    assert parse_compact_expiry_date("28FEB2025") == "2025-02-28"
    assert parse_compact_expiry_date("04-SEP-2026") == "2026-09-04"
    assert parse_compact_expiry_date("2026-12-05") == "2026-12-05"

def test_compact_expiry_invalid():
    with pytest.raises(ValueError):
        parse_compact_expiry_date("INVALID_EXPIRY")

# 3. Actual Trading Date Parsing (handling MM/DD/YYYY returned by MCX)
def test_actual_trading_date_parsing_mm_dd_yyyy():
    req_dt = datetime(2026, 9, 15)  # 15th September 2026
    # MCX file returns MM/DD/YYYY (09/15/2026)
    parsed = parse_trading_date("09/15/2026", target_dt=req_dt)
    assert parsed == "2026-09-15"

# 4. Symbol Padding Trimming and Numeric Cleaning
def test_symbol_padding_and_numeric_cleaning():
    csv_data = """Commodity,Date,ExpiryDate,Open,High,Low,Close,Volume,OpenInterest
GOLDM   ,15/09/2026,05NOV2026,"75,100.00","75,400.00","74,900.00","75,250.00","1,200","5,400"
  GOLDPETAL  ,15/09/2026,05NOV2026,7520.00,7550.00,7510.00,7540.00,4500,20000
"""
    result = parse_mcx_bhavcopy_file(csv_data, requested_date_str="15/09/2026")
    assert result["success"] is True
    assert result["status"] == "SUCCESS"
    assert len(result["records"]) == 2

    # Check trimmed symbols
    symbols = [r["symbol"] for r in result["records"]]
    assert "GOLDM" in symbols
    assert "GOLDPETAL" in symbols

    # Check parsed numeric prices
    goldm = next(r for r in result["records"] if r["symbol"] == "GOLDM")
    assert goldm["close"] == 75250.0
    assert goldm["volume"] == 1200
    assert goldm["open_interest"] == 5400

# 5. Contract Identified by Symbol + Expiry, Never Symbol Alone
def test_contract_identified_by_symbol_and_expiry():
    csv_data = """Symbol,Date,ExpiryDate,Open,High,Low,Close,Volume,OpenInterest
GOLDM,15/09/2026,05OCT2026,75000,75300,74900,75200,1000,5000
GOLDM,15/09/2026,05DEC2026,75600,75900,75500,75800,400,2000
"""
    result = parse_mcx_bhavcopy_file(csv_data, requested_date_str="15/09/2026")
    assert result["success"] is True
    assert len(result["records"]) == 2

    # Verify distinct contract IDs
    contract_ids = [r["contract_id"] for r in result["records"]]
    assert "GOLDM_2026-10-05" in contract_ids
    assert "GOLDM_2026-12-05" in contract_ids

# 6. Duplicate Rows Handled Gracefully
def test_duplicate_records_handling():
    csv_data = """Symbol,Date,ExpiryDate,Open,High,Low,Close,Volume,OpenInterest
GOLDM,15/09/2026,05NOV2026,75000,75300,74900,75200,1000,5000
GOLDM,15/09/2026,05NOV2026,75000,75300,74900,75200,1000,5000
"""
    result = parse_mcx_bhavcopy_file(csv_data, requested_date_str="15/09/2026")
    assert result["success"] is True
    assert len(result["records"]) == 1
    assert result["validation_report"]["duplicate_count"] == 1

# 7. Reject Responses Whose Actual Date Differs from Requested Date
def test_reject_incorrect_returned_dates():
    # User requested Monday 2026-09-21, but file contains Friday 2026-09-18 data
    csv_data = """Symbol,Date,ExpiryDate,Open,High,Low,Close,Volume,OpenInterest
GOLDM,18/09/2026,05NOV2026,75000,75300,74900,75200,1000,5000
GOLDPETAL,18/09/2026,05NOV2026,7520,7550,7510,7540,4000,15000
"""
    result = parse_mcx_bhavcopy_file(csv_data, requested_date_str="21/09/2026")
    assert result["success"] is False
    assert result["status"] == "DATE_MISMATCH"
    assert result["actual_data_date"] == "2026-09-18"
    assert result["requested_date"] == "2026-09-21"
    assert "Date mismatch" in result["message"]
    # Ensure zero market data records accepted
    assert len(result["records"]) == 0

# 8. Raw Records and Validation Storage in SQLite
def test_raw_records_and_validation_storage_sqlite():
    csv_data = """Symbol,Date,ExpiryDate,Open,High,Low,Close,Volume,OpenInterest
GOLDM,15/09/2026,05NOV2026,75000,75300,74900,75200,1000,5000
GOLDTEN,15/09/2026,05NOV2026,75050,75350,74950,-50,500,2000
"""
    # Second row has negative close (-50), should be rejected
    result = parse_mcx_bhavcopy_file(csv_data, requested_date_str="15/09/2026")
    import_id = save_bhavcopy_import_audit(result, source="TEST_UPLOAD")
    assert import_id > 0

    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check raw_bhavcopy_imports
        cursor.execute("SELECT * FROM raw_bhavcopy_imports WHERE id = ?;", (import_id,))
        imp = dict(cursor.fetchone())
        assert imp["source"] == "TEST_UPLOAD"
        assert imp["valid_rows_count"] == 1
        assert imp["rejected_rows_count"] == 1

        # Check raw_bhavcopy_records
        cursor.execute("SELECT * FROM raw_bhavcopy_records WHERE import_id = ?;", (import_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        assert len(rows) == 2

        # Check validation_logs
        cursor.execute("SELECT * FROM validation_logs WHERE import_id = ?;", (import_id,))
        val_logs = [dict(r) for r in cursor.fetchall()]
        assert len(val_logs) >= 1
        assert "positive" in val_logs[0]["reason"].lower()

# 9. Test with genuine downloaded Bhavcopy file from disk
def test_genuine_downloaded_bhavcopy_file_ingestion():
    import os
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "mcx_bhavcopy_genuine_sample.csv")
    assert os.path.exists(fixture_path), f"Fixture file not found at {fixture_path}"

    with open(fixture_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse with matching requested date (15/09/2026)
    result = parse_mcx_bhavcopy_file(content, requested_date_str="15/09/2026", source="GENUINE_BHAVCOPY_FILE")
    assert result["success"] is True
    assert result["status"] == "SUCCESS"
    assert result["actual_data_date"] == "2026-09-15"
    assert result["requested_date"] == "2026-09-15"
    
    # 5 gold records parsed (GOLDM Oct, GOLDM Dec, GOLDTEN Oct, GOLDGUINEA Sep, GOLDPETAL Sep)
    records = result["records"]
    assert len(records) == 5

    # Check contract IDs and values
    contract_ids = {r["contract_id"] for r in records}
    assert "GOLDM_2026-10-05" in contract_ids
    assert "GOLDM_2026-12-05" in contract_ids
    assert "GOLDTEN_2026-10-05" in contract_ids
    assert "GOLDGUINEA_2026-09-30" in contract_ids
    assert "GOLDPETAL_2026-09-30" in contract_ids

    # Verify numerical parsing cleaned string commas
    goldm_oct = next(r for r in records if r["contract_id"] == "GOLDM_2026-10-05")
    assert goldm_oct["close"] == 75280.0
    assert goldm_oct["volume"] == 1450
    assert goldm_oct["open_interest"] == 6120

    petal_sep = next(r for r in records if r["contract_id"] == "GOLDPETAL_2026-09-30")
    assert petal_sep["close"] == 7560.0
    assert petal_sep["volume"] == 5200

    # Save to SQLite database and verify persistence
    import_id = save_bhavcopy_import_audit(result, source="GENUINE_BHAVCOPY_FILE")
    assert import_id > 0

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM market_data WHERE trade_date = '2026-09-15';")
        saved_count = cursor.fetchone()["cnt"]
        assert saved_count >= 5

# 10. Confirm date validator rejects mismatched date against genuine Bhavcopy file
def test_genuine_downloaded_bhavcopy_mismatched_date_rejection():
    import os
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "mcx_bhavcopy_genuine_sample.csv")
    with open(fixture_path, "r", encoding="utf-8") as f:
        content = f.read()

    # User requested 16/09/2026, but genuine file contains 15/09/2026 data
    result = parse_mcx_bhavcopy_file(content, requested_date_str="16/09/2026", source="GENUINE_BHAVCOPY_FILE")
    assert result["success"] is False
    assert result["status"] == "DATE_MISMATCH"
    assert result["requested_date"] == "2026-09-16"
    assert result["actual_data_date"] == "2026-09-15"
    assert "Date mismatch" in result["message"]
    assert len(result["records"]) == 0

