"""
AurumIQ Comprehensive End-to-End Audit & Regression Suite
Tests Genuine MCX Bhavcopy upload, parsing, date validation, SQLite persistence,
contract-expiry-aware filtering, normalization, spread calculations, signal generation,
backtesting, invalid files, missing dates, duplicate rows, mismatched trading dates,
and insufficient history.
"""
import io
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.connection import init_db, get_db

client = TestClient(app)

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "mcx_bhavcopy_genuine_sample.csv")


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


# -------------------------------------------------------------
# 1. GENUINE BHAVCOPY UPLOAD, PARSING & SQLITE PERSISTENCE
# -------------------------------------------------------------
def test_genuine_bhavcopy_upload_and_persistence():
    """Upload genuine MCX Bhavcopy file and verify database records."""
    assert os.path.exists(FIXTURE_PATH), f"Fixture not found at {FIXTURE_PATH}"

    # Reset DB to ensure isolated count verification
    client.post("/api/data-quality/reset")

    with open(FIXTURE_PATH, "rb") as f:
        file_bytes = f.read()

    # Upload with matching requested date
    res = client.post(
        "/api/bhavcopy/upload",
        files={"file": ("mcx_bhavcopy.csv", io.BytesIO(file_bytes), "text/csv")},
        data={"requested_date": "15/09/2026"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["status"] == "SUCCESS"
    assert data["requested_date"] == "2026-09-15"
    assert data["actual_data_date"] == "2026-09-15"

    records = data["records"]
    assert len(records) == 5  # 5 gold contract rows in fixture

    # Verify SQLite persistence
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM market_data WHERE trade_date = '2026-09-15';")
        count = cursor.fetchone()["count"]
        assert count == 5

        # Check raw audit tables
        cursor.execute("SELECT * FROM raw_bhavcopy_imports WHERE id = ?;", (data["import_id"],))
        imp = cursor.fetchone()
        assert imp is not None
        assert imp["status"] == "SUCCESS"
        assert imp["valid_rows_count"] == 5
        assert imp["rejected_rows_count"] == 0

        cursor.execute("SELECT COUNT(*) as rc FROM raw_bhavcopy_records WHERE import_id = ?;", (data["import_id"],))
        assert cursor.fetchone()["rc"] == 5


# -------------------------------------------------------------
# 2. INVALID FILES TESTING (EMPTY, MALFORMED, MISSING HEADERS)
# -------------------------------------------------------------
def test_upload_empty_file():
    """Uploading an empty file must be rejected cleanly."""
    res = client.post(
        "/api/bhavcopy/upload",
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
        data={"requested_date": "15/09/2026"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert data["status"] == "EMPTY_FILE"
    assert "empty" in data["message"].lower()
    assert len(data["records"]) == 0


def test_upload_missing_columns():
    """Uploading a file missing mandatory price columns must be rejected."""
    bad_csv = "Commodity,Date,ExpiryDate,Volume\nGOLDM,15/09/2026,05OCT2026,100\n"
    res = client.post(
        "/api/bhavcopy/upload",
        files={"file": ("missing_cols.csv", io.BytesIO(bad_csv.encode("utf-8")), "text/csv")},
        data={"requested_date": "15/09/2026"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert data["status"] == "MISSING_COLUMNS"
    assert "close" in data["message"].lower() or "missing" in data["message"].lower()


def test_upload_no_gold_contracts():
    """Uploading a file containing only non-gold commodities must return NO_GOLD_CONTRACTS."""
    silver_csv = (
        "Commodity,Date,ExpiryDate,Open,High,Low,Close,Volume,OpenInterest\n"
        "SILVER,15/09/2026,05DEC2026,89000,89500,88500,89200,500,2000\n"
        "CRUDEOIL,15/09/2026,19OCT2026,6100,6200,6050,6150,2000,5000\n"
    )
    res = client.post(
        "/api/bhavcopy/upload",
        files={"file": ("other_commodities.csv", io.BytesIO(silver_csv.encode("utf-8")), "text/csv")},
        data={"requested_date": "15/09/2026"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert data["status"] == "NO_GOLD_CONTRACTS"
    assert len(data["records"]) == 0


# -------------------------------------------------------------
# 3. MISSING DATES TESTING
# -------------------------------------------------------------
def test_missing_trade_and_expiry_dates():
    """Rows with missing/invalid trade dates or expiry dates must be rejected and audited."""
    csv_missing_dates = (
        "Commodity,Date,ExpiryDate,Open,High,Low,Close,Volume,OpenInterest\n"
        "GOLDM,,05OCT2026,75000,75500,74900,75200,100,500\n"  # missing trade date
        "GOLDTEN,15/09/2026,,75100,75600,75000,75300,50,200\n"  # missing expiry date
        "GOLDPETAL,15/09/2026,30SEP2026,7520,7560,7510,7540,500,2000\n"  # valid row
    )
    res = client.post(
        "/api/bhavcopy/upload",
        files={"file": ("missing_dates.csv", io.BytesIO(csv_missing_dates.encode("utf-8")), "text/csv")},
        data={"requested_date": "15/09/2026"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["records"]) == 1  # only GOLDPETAL is valid
    assert data["records"][0]["symbol"] == "GOLDPETAL"
    assert data["validation_report"]["rejected_count"] == 2


# -------------------------------------------------------------
# 4. DUPLICATE ROWS TESTING
# -------------------------------------------------------------
def test_duplicate_contract_rows_handling():
    """Duplicate rows for the same contract on the same date must be deduplicated."""
    dup_csv = (
        "Commodity,Date,ExpiryDate,Open,High,Low,Close,Volume,OpenInterest\n"
        "GOLDM,15/09/2026,05OCT2026,75100,75400,75000,75250,500,2000\n"
        "GOLDM,15/09/2026,05OCT2026,75100,75400,75000,75250,500,2000\n"  # Exact duplicate
        "GOLDM,15/09/2026,05OCT2026,75100,75400,75000,75250,500,2000\n"  # Second duplicate
    )
    res = client.post(
        "/api/bhavcopy/upload",
        files={"file": ("duplicates.csv", io.BytesIO(dup_csv.encode("utf-8")), "text/csv")},
        data={"requested_date": "15/09/2026"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["records"]) == 1  # Only 1 unique record stored
    assert data["validation_report"]["duplicate_count"] == 2


# -------------------------------------------------------------
# 5. MISMATCHED TRADING DATES TESTING
# -------------------------------------------------------------
def test_mismatched_trading_date_rejection():
    """
    If requested date is 18/09/2026 but file contains 15/09/2026,
    the system must strictly reject the file with DATE_MISMATCH.
    """
    with open(FIXTURE_PATH, "rb") as f:
        file_bytes = f.read()

    res = client.post(
        "/api/bhavcopy/upload",
        files={"file": ("bhavcopy.csv", io.BytesIO(file_bytes), "text/csv")},
        data={"requested_date": "18/09/2026"}  # Mismatched date
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert data["status"] == "DATE_MISMATCH"
    assert data["requested_date"] == "2026-09-18"
    assert data["actual_data_date"] == "2026-09-15"
    assert "Date mismatch" in data["message"]
    assert len(data["records"]) == 0

    # Ensure zero market data records were inserted
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM market_data WHERE trade_date = '2026-09-18';")
        assert cursor.fetchone()["cnt"] == 0


# -------------------------------------------------------------
# 6. CONTRACT-EXPIRY-AWARE FILTERING & NORMALIZATION
# -------------------------------------------------------------
def test_contract_expiry_aware_filtering_and_normalization():
    """
    Ingest sample multi-expiry historical data and verify expiry filtering
    and uniform 10g normalization.
    """
    # Load 120-day historical sample
    res_load = client.post("/api/data-quality/ingest-sample")
    assert res_load.status_code == 200

    # Check available expiries
    res_exp = client.get("/api/expiries")
    assert res_exp.status_code == 200
    expiries = res_exp.json()["expiries"]
    assert "GOLDM" in expiries and len(expiries["GOLDM"]) > 1

    near_exp = expiries["GOLDM"][0]
    far_exp = expiries["GOLDM"][1]

    # Query spreads for near-month vs near-month
    res_spread_near = client.get(
        f"/api/spreads?pair_a=GOLDM&expiry_a={near_exp}&pair_b=GOLDPETAL&lookback=15"
    )
    assert res_spread_near.status_code == 200
    data_near = res_spread_near.json()
    assert data_near["has_data"] is True
    assert len(data_near["series"]) > 0

    # Verify that series uses normalized ₹/10g values
    sample_pt = data_near["series"][0]
    assert "price_a" in sample_pt
    assert "price_b" in sample_pt
    assert 60000.0 <= sample_pt["price_a"] <= 90000.0  # reasonable gold 10g price range
    assert 60000.0 <= sample_pt["price_b"] <= 90000.0


# -------------------------------------------------------------
# 7. INSUFFICIENT HISTORY TESTING (SPREADS & BACKTEST)
# -------------------------------------------------------------
def test_insufficient_history_spread_engine():
    """
    When available concurrent trading sessions are fewer than min_observations,
    spread engine must return NO_SIGNAL and is_actionable=False without inventing prices.
    """
    # Reset database first
    client.post("/api/data-quality/reset")

    # Ingest only a single day of Bhavcopy data
    with open(FIXTURE_PATH, "rb") as f:
        file_bytes = f.read()

    client.post(
        "/api/bhavcopy/upload",
        files={"file": ("bhavcopy.csv", io.BytesIO(file_bytes), "text/csv")},
        data={"requested_date": "15/09/2026"}
    )

    # Query spreads with lookback=20, min_observations=10 (only 1 day in DB!)
    res = client.get("/api/spreads?pair_a=GOLDM&pair_b=GOLDPETAL&lookback=20&min_observations=10")
    assert res.status_code == 200
    data = res.json()
    assert data["has_data"] is False
    assert data["statistics"] is None  # Cannot compute rolling stats on 1 day
    assert data["signal"]["is_actionable"] is False
    assert data["signal"]["signal_type"] == "NO_SIGNAL"
    assert any("Insufficient history" in w for w in data["data_quality_warnings"])


def test_insufficient_history_backtesting_engine():
    """
    Backtesting engine must reject insufficient data (< 30 sessions)
    with a clear message and success=False, without fabricating fake backtest results.
    """
    # Reset database to empty
    client.post("/api/data-quality/reset")

    # Upload single day
    with open(FIXTURE_PATH, "rb") as f:
        file_bytes = f.read()
    client.post(
        "/api/bhavcopy/upload",
        files={"file": ("bhavcopy.csv", io.BytesIO(file_bytes), "text/csv")},
        data={"requested_date": "15/09/2026"}
    )

    payload = {
        "pair_a": "GOLDM",
        "pair_b": "GOLDPETAL",
        "entry_z": 1.5,
        "exit_z": 0.2,
        "stop_loss_z": 3.0,
        "lookback": 20,
        "initial_capital": 500000
    }
    res = client.post("/api/backtest/run", json=payload)
    assert res.status_code == 200
    bt = res.json()
    assert bt["success"] is False
    assert "Insufficient data" in bt["message"]
    assert bt["metrics"] is None


# -------------------------------------------------------------
# 8. END-TO-END WALK-FORWARD BACKTEST & CSV AUDIT REPORT
# -------------------------------------------------------------
def test_full_walk_forward_backtest_and_report_export():
    """
    Load full historical data, execute 3-way chronological walk-forward simulation,
    and download the audit report CSV.
    """
    # Ingest 120-day historical data
    client.post("/api/data-quality/ingest-sample")

    payload = {
        "pair_a": "GOLDM",
        "pair_b": "GOLDPETAL",
        "entry_z": 1.5,
        "exit_z": 0.2,
        "stop_loss_z": 3.0,
        "lookback": 20,
        "initial_capital": 500000,
        "include_friction": True,
        "dev_ratio": 0.50,
        "val_ratio": 0.25,
        "test_ratio": 0.25
    }

    # Execute simulation
    res = client.post("/api/backtest/run", json=payload)
    assert res.status_code == 200
    bt = res.json()
    assert bt["success"] is True

    # Verify walk-forward partitions exist
    splits = bt["walk_forward_splits"]
    assert "development" in splits
    assert "validation" in splits
    assert "unseen_test" in splits

    # Verify benchmark comparison metrics
    bench = bt["benchmark_comparison"]
    assert "alpha_pct" in bench
    assert "beta" in bench
    assert "information_ratio" in bench

    # Verify CSV export
    res_rep = client.post("/api/backtest/report", json=payload)
    assert res_rep.status_code == 200
    assert "text/csv" in res_rep.headers["content-type"]
    assert "STRATEGY SPECIFICATION" in res_rep.text
    assert "CHRONOLOGICAL WALK-FORWARD PARTITIONS" in res_rep.text


# -------------------------------------------------------------
# 9. ADVANCED INVALID FILES & OHLC SANITY REJECTIONS
# -------------------------------------------------------------
def test_invalid_files_malformed_syntax_and_corrupt_data():
    """
    Test various invalid file formats:
    - Inverted OHLC (High < Low, High < Open, Low > Close)
    - Negative prices
    - Out of bounds prices (< ₹30,000 or > ₹180,000)
    - Non-numeric prices
    """
    # Inverted OHLC: High (74000) < Low (75000)
    csv_inverted_ohlc = (
        "Commodity,Date,ExpiryDate,Open,High,Low,Close,Volume,OpenInterest\n"
        "GOLDM,15/09/2026,05OCT2026,75100,74000,75000,74500,100,500\n"
    )
    res = client.post(
        "/api/bhavcopy/upload",
        files={"file": ("inverted_ohlc.csv", io.BytesIO(csv_inverted_ohlc.encode("utf-8")), "text/csv")},
        data={"requested_date": "15/09/2026"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert data["validation_report"]["rejected_count"] == 1
    assert any("lower than" in r["reason"].lower() for r in data["validation_report"]["rejected_samples"])

    # Negative price
    csv_negative = (
        "Commodity,Date,ExpiryDate,Open,High,Low,Close,Volume,OpenInterest\n"
        "GOLDM,15/09/2026,05OCT2026,75100,75500,74900,-500,100,500\n"
    )
    res_neg = client.post(
        "/api/bhavcopy/upload",
        files={"file": ("negative_price.csv", io.BytesIO(csv_negative.encode("utf-8")), "text/csv")},
        data={"requested_date": "15/09/2026"}
    )
    assert res_neg.status_code == 200
    data_neg = res_neg.json()
    assert data_neg["success"] is False
    assert data_neg["validation_report"]["rejected_count"] == 1
    assert any("strictly positive" in r["reason"].lower() for r in data_neg["validation_report"]["rejected_samples"])

    # Non-numeric string price
    csv_text_price = (
        "Commodity,Date,ExpiryDate,Open,High,Low,Close,Volume,OpenInterest\n"
        "GOLDM,15/09/2026,05OCT2026,75100,75500,74900,N.A.,100,500\n"
    )
    res_txt = client.post(
        "/api/bhavcopy/upload",
        files={"file": ("text_price.csv", io.BytesIO(csv_text_price.encode("utf-8")), "text/csv")},
        data={"requested_date": "15/09/2026"}
    )
    assert res_txt.status_code == 200
    data_txt = res_txt.json()
    assert data_txt["success"] is False
    assert data_txt["validation_report"]["rejected_count"] == 1


# -------------------------------------------------------------
# 10. DATE CORRUPTION & EXPIRY-BEFORE-TRADE-DATE REJECTION
# -------------------------------------------------------------
def test_expiry_date_prior_to_trade_date():
    """
    Expiry date earlier than trading date must be rejected immediately
    and logged in the rejection audit trail.
    """
    csv_expired = (
        "Commodity,Date,ExpiryDate,Open,High,Low,Close,Volume,OpenInterest\n"
        "GOLDM,15/09/2026,05AUG2026,75100,75500,74900,75200,100,500\n"  # Expiry in August, Trade in September
    )
    res = client.post(
        "/api/bhavcopy/upload",
        files={"file": ("expired.csv", io.BytesIO(csv_expired.encode("utf-8")), "text/csv")},
        data={"requested_date": "15/09/2026"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert data["validation_report"]["rejected_count"] == 1
    assert any("before trade date" in r["reason"].lower() for r in data["validation_report"]["rejected_samples"])


# -------------------------------------------------------------
# 11. GENUINE BHAVCOPY NORMALIZATION MATHEMATICAL ACCURACY
# -------------------------------------------------------------
def test_genuine_bhavcopy_normalization_exact_math():
    """
    Verify exact 10g base normalization and purity-adjustment for all 4 contracts
    from the genuine MCX Bhavcopy file.
    """
    client.post("/api/data-quality/reset")

    with open(FIXTURE_PATH, "rb") as f:
        file_bytes = f.read()

    res = client.post(
        "/api/bhavcopy/upload",
        files={"file": ("mcx_bhavcopy.csv", io.BytesIO(file_bytes), "text/csv")},
        data={"requested_date": "15/09/2026"}
    )
    assert res.status_code == 200
    records = res.json()["records"]

    rec_by_id = {r["contract_id"]: r for r in records}

    # 1. GOLDM (Near: 05OCT2026): close=75280 -> 10g base = 75280.00, 995 purity -> purity_adj = 75280 * (999/995)
    goldm_near = rec_by_id["GOLDM_2026-10-05"]
    assert goldm_near["close"] == 75280.00
    assert goldm_near["normalized_close_10g"] == 75280.00
    expected_purity_goldm = round(75280.00 * (999.0 / 995.0), 2)
    assert goldm_near["purity_adjusted_10g"] == expected_purity_goldm

    # 2. GOLDTEN: close=75340 -> 10g base = 75340.00, 999 purity -> purity_adj = 75340.00
    goldten = rec_by_id["GOLDTEN_2026-10-05"]
    assert goldten["close"] == 75340.00
    assert goldten["normalized_close_10g"] == 75340.00
    assert goldten["purity_adjusted_10g"] == 75340.00

    # 3. GOLDGUINEA: close=60450 -> 8g quote -> 10g base = 60450 * 1.25 = 75562.50, 995 purity -> purity_adj = 75562.50 * (999/995) = 75866.27
    guinea = rec_by_id["GOLDGUINEA_2026-09-30"]
    assert guinea["close"] == 60450.00
    assert guinea["normalized_close_10g"] == 75562.50
    expected_purity_guinea = round(75562.50 * (999.0 / 995.0), 2)
    assert guinea["purity_adjusted_10g"] == expected_purity_guinea

    # 4. GOLDPETAL: close=7560 -> 1g quote -> 10g base = 7560 * 10 = 75600.00
    petal = rec_by_id["GOLDPETAL_2026-09-30"]
    assert petal["close"] == 7560.00
    assert petal["normalized_close_10g"] == 75600.00
    assert petal["purity_adjusted_10g"] == 75600.00

    # Verify overview endpoint outputs the near-month quotes and spread matrix
    res_ov = client.get("/api/overview")
    assert res_ov.status_code == 200
    ov_data = res_ov.json()
    assert ov_data["has_data"] is True
    matrix = ov_data["spread_matrix"]
    assert len(matrix) == 4

    # Verify spread between GOLDM and GOLDPETAL in matrix: 75280 - 75600 = -320.00
    goldm_row = next(m for m in matrix if m["symbol"] == "GOLDM")
    assert goldm_row["GOLDPETAL"] == -320.00


# -------------------------------------------------------------
# 12. DIRECT MCX DOWNLOAD ENDPOINT AUDIT (REPORTING BLOCKED STATUS)
# -------------------------------------------------------------
def test_direct_mcx_download_investigation_and_status_reporting():
    """
    Test direct download endpoint with a genuine trading date.
    Verifies that real exchange behavior (WAF block / dynamic ASPX page)
    is cleanly reported without fabricating missing data.
    """
    res = client.post(
        "/api/bhavcopy/download",
        json={"requested_date": "15/09/2026"}
    )
    assert res.status_code == 200
    data = res.json()
    # The endpoint will return either FETCH_BLOCKED, DYNAMIC_PORTAL_INTERACTION_REQUIRED, or NETWORK_ERROR
    # and MUST NOT fabricate fake prices or fake successful downloads!
    assert "status" in data
    assert "import_id" in data
    assert data["requested_date"] == "2026-09-15"
    if not data["success"]:
        assert data["status"] in ["FETCH_BLOCKED", "DYNAMIC_PORTAL_INTERACTION_REQUIRED", "NETWORK_ERROR", "HTTP_ERROR_403"]
        assert len(data["records"]) == 0
        # Audit record must exist in raw_bhavcopy_imports
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM raw_bhavcopy_imports WHERE id = ?;", (data["import_id"],))
            imp = cursor.fetchone()
            assert imp is not None
            assert imp["source"] == "MCX_DIRECT_DOWNLOAD"


# -------------------------------------------------------------
# 13. FILE UPLOAD EXTENSION & EMPTY PAYLOAD GUARDS
# -------------------------------------------------------------
def test_bhavcopy_upload_invalid_extension():
    """Verify that uploading non-csv/non-txt files is rejected with HTTP 400."""
    res = client.post(
        "/api/bhavcopy/upload",
        files={"file": ("malicious_payload.exe", io.BytesIO(b"executable content"), "application/octet-stream")},
        data={"requested_date": "15/09/2026"}
    )
    assert res.status_code == 400
    assert "Invalid file format" in res.json()["detail"]


def test_bhavcopy_upload_empty_file():
    """Verify that uploading an empty file (0 bytes) is audited and returned with EMPTY_FILE status."""
    res = client.post(
        "/api/bhavcopy/upload",
        files={"file": ("empty_bhavcopy.csv", io.BytesIO(b""), "text/csv")},
        data={"requested_date": "15/09/2026"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "EMPTY_FILE"

