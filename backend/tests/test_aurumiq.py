"""
AurumIQ Comprehensive Automated Test Suite
Tests Normalization, Validation, Spread Signals, Backtesting Engine, and API Health.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.connection import init_db
from app.config import CONTRACT_SPECS
from app.validation.validator import validate_market_record, validate_batch
from app.normalization.normalizer import normalize_single_record, normalize_market_records
from app.signal.spread_engine import calculate_spread_series
from app.backtesting.engine import run_spread_backtest, calculate_mcx_trade_cost
import pandas as pd
import numpy as np

# Ensure DB initialized
init_db()

client = TestClient(app)

# 1. API Health & Initial Empty State Test
def test_health_check_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "total_market_records" in data
    assert data["database"] == "sqlite_connected"

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "AurumIQ API"

# 2. Contract Normalization Tests
def test_contract_multipliers():
    # GOLDM: 10g base -> multiplier = 1.0
    assert CONTRACT_SPECS["GOLDM"].multiplier_to_10g == 1.0
    # GOLDTEN: 10g base -> multiplier = 1.0
    assert CONTRACT_SPECS["GOLDTEN"].multiplier_to_10g == 1.0
    # GOLDGUINEA: 8g base -> multiplier = 1.25 (10 / 8)
    assert CONTRACT_SPECS["GOLDGUINEA"].multiplier_to_10g == 1.25
    # GOLDPETAL: 1g base -> multiplier = 10.0
    assert CONTRACT_SPECS["GOLDPETAL"].multiplier_to_10g == 10.0

def test_price_normalization_math():
    # If GOLDPETAL is ₹7,500 for 1g, normalized 10g must be exactly ₹75,000
    petal_record = {
        "symbol": "GOLDPETAL",
        "trade_date": "2026-10-01",
        "expiry_date": "2026-11-05",
        "open": 7490.0,
        "high": 7520.0,
        "low": 7480.0,
        "close": 7500.0,
        "volume": 1000,
        "open_interest": 5000
    }
    norm = normalize_single_record(petal_record)
    assert norm["normalized_close_10g"] == 75000.0
    assert norm["dte"] == 35

    # If GOLDGUINEA is ₹60,000 for 8g, normalized 10g must be 60,000 * 1.25 = ₹75,000
    guinea_record = {
        "symbol": "GOLDGUINEA",
        "trade_date": "2026-10-01",
        "expiry_date": "2026-11-05",
        "open": 59900.0,
        "high": 60100.0,
        "low": 59800.0,
        "close": 60000.0,
        "volume": 500,
        "open_interest": 2000
    }
    norm_g = normalize_single_record(guinea_record)
    assert norm_g["normalized_close_10g"] == 75000.0

# 3. Validation Tests
def test_validation_rejects_negative_price():
    bad_record = {
        "symbol": "GOLDM",
        "trade_date": "2026-10-01",
        "expiry_date": "2026-11-05",
        "open": 75000.0,
        "high": 75500.0,
        "low": -10.0,
        "close": 75200.0,
        "volume": 100,
        "open_interest": 500
    }
    ok, reason, _ = validate_market_record(bad_record)
    assert not ok
    assert "positive" in reason.lower()

def test_validation_rejects_inverted_ohlc():
    bad_record = {
        "symbol": "GOLDM",
        "trade_date": "2026-10-01",
        "expiry_date": "2026-11-05",
        "open": 75000.0,
        "high": 74000.0,  # High lower than Open/Close
        "low": 73500.0,
        "close": 74800.0,
        "volume": 100,
        "open_interest": 500
    }
    ok, reason, _ = validate_market_record(bad_record)
    assert not ok
    assert "high" in reason.lower()

# 4. Spread Signal & Half-Life Engine Test
def test_spread_calculation_and_zscore():
    dates = pd.date_range("2026-01-01", periods=30, freq="B").strftime("%Y-%m-%d")
    np.random.seed(123)
    p_a = 75000 + np.cumsum(np.random.normal(0, 100, 30))
    p_b = p_a + 25 + np.random.normal(0, 10, 30)  # Spread mean ~ -25
    
    df_a = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": p_a,
        "volume": 1000,
        "open_interest": 5000,
        "dte": 30
    })
    df_b = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": p_b,
        "volume": 1000,
        "open_interest": 5000,
        "dte": 30
    })
    
    res = calculate_spread_series(df_a, df_b, "GOLDM", "GOLDPETAL", lookback=10)
    assert res["message"] == "Success"
    assert len(res["series"]) == 30
    assert "statistics" in res
    assert res["statistics"]["current_spread"] is not None
    assert res["statistics"]["half_life_days"] is not None

# 5. MCX Transaction Fee Model Test
def test_mcx_transaction_fee_calculation():
    notional = 1000000.0  # ₹10 Lakhs turnover
    cost_buy = calculate_mcx_trade_cost(notional, is_buy=True)
    cost_sell = calculate_mcx_trade_cost(notional, is_buy=False)
    # Sell side includes CTT (0.01%), buy side includes stamp duty (0.002%)
    assert cost_sell > cost_buy
    assert cost_buy > 0.0

# 6. Backtest Strategy Execution Test
def test_backtest_execution():
    dates = pd.date_range("2026-01-01", periods=40, freq="B").strftime("%Y-%m-%d")
    np.random.seed(42)
    spread_pattern = np.sin(np.linspace(0, 4 * np.pi, 40)) * 50.0  # Oscillating spread
    base = 75000.0
    p_a = base + spread_pattern / 2.0
    p_b = base - spread_pattern / 2.0
    
    df_a = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": p_a,
        "volume": 2000,
        "open_interest": 8000,
        "dte": 25
    })
    df_b = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": p_b,
        "volume": 3000,
        "open_interest": 9000,
        "dte": 25
    })
    
    res = run_spread_backtest(
        df_a, df_b, "GOLDM", "GOLDPETAL",
        entry_z=1.0, exit_z=0.2, lookback=10, initial_capital=500000.0
    )
    assert res["success"] is True
    assert "metrics" in res
    assert res["metrics"]["total_trades"] > 0
    assert len(res["equity_curve"]) == 40

# 7. Data Quality & Empty State API Test
def test_data_quality_endpoint():
    response = client.get("/api/data-quality")
    assert response.status_code == 200
    data = response.json()
    assert "total_records" in data

# 8. Zero Variance Test
def test_zero_variance_spread():
    dates = pd.date_range("2026-01-01", periods=25, freq="B").strftime("%Y-%m-%d")
    # Perfectly flat spread of exactly ₹20.0
    p_a = np.full(25, 75000.0)
    p_b = np.full(25, 74980.0)
    
    df_a = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": p_a,
        "raw_close": p_a,
        "volume": 1000,
        "open_interest": 5000,
        "dte": 30
    })
    df_b = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": p_b,
        "raw_close": p_b,
        "volume": 1000,
        "open_interest": 5000,
        "dte": 30
    })
    
    res = calculate_spread_series(df_a, df_b, "GOLDM", "GOLDPETAL", lookback=15)
    assert res["message"] == "Success"
    # Zero variance must be flagged
    assert any("Zero spread variance" in w for w in res["data_quality_warnings"])
    assert res["signal"]["signal_type"] == "NO_SIGNAL"
    assert "No actionable signal" in res["signal"]["signal_label"]
    assert res["signal"]["is_actionable"] is False
    assert any("Zero spread variance" in r for r in res["signal"]["reasons"])
    assert "ANALYTICAL INFORMATION ONLY" in res["disclaimer"]

# 9. Missing Observations & Calendar Gaps Test
def test_missing_observations_and_calendar_gaps():
    # 20 business dates, but with a 10-day calendar jump in the middle
    dates_part1 = pd.date_range("2026-01-01", periods=10, freq="B").strftime("%Y-%m-%d").tolist()
    dates_part2 = pd.date_range("2026-01-25", periods=10, freq="B").strftime("%Y-%m-%d").tolist()
    all_dates_a = dates_part1 + dates_part2
    
    # Contract B missing 2 dates from part 1
    all_dates_b = dates_part1[:-2] + dates_part2
    
    df_a = pd.DataFrame({
        "trade_date": all_dates_a,
        "normalized_close_10g": np.linspace(74000, 75000, len(all_dates_a)),
        "raw_close": np.linspace(74000, 75000, len(all_dates_a)),
        "volume": 500,
        "open_interest": 2000,
        "dte": 30
    })
    df_b = pd.DataFrame({
        "trade_date": all_dates_b,
        "normalized_close_10g": np.linspace(74020, 75020, len(all_dates_b)),
        "raw_close": np.linspace(74020, 75020, len(all_dates_b)),
        "volume": 500,
        "open_interest": 2000,
        "dte": 30
    })
    
    res = calculate_spread_series(df_a, df_b, "GOLDM", "GOLDGUINEA", lookback=10)
    assert res["message"] == "Success"
    # Calendar gap warning
    assert any("Missing observations" in w and "gap in trading dates" in w for w in res["data_quality_warnings"])
    # Asymmetric calendar warning
    assert any("Missing observations" in w and "trading session(s)" in w for w in res["data_quality_warnings"])
    # Overlapping dates cleanly merged
    assert len(res["series"]) == len(all_dates_b)

# 10. Insufficient History Test
def test_insufficient_history():
    dates = pd.date_range("2026-01-01", periods=5, freq="B").strftime("%Y-%m-%d")
    df_a = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": [75000.0] * 5,
        "volume": 100,
        "open_interest": 500,
        "dte": 20
    })
    df_b = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": [75020.0] * 5,
        "volume": 100,
        "open_interest": 500,
        "dte": 20
    })
    
    # Require 10 observations, only 5 provided
    res = calculate_spread_series(df_a, df_b, "GOLDM", "GOLDPETAL", min_observations=10)
    assert res["series"] == []
    assert res["signal"]["signal_type"] == "NO_SIGNAL"
    assert res["signal"]["signal_label"] == "No actionable signal"
    assert res["signal"]["is_actionable"] is False
    assert any("Insufficient history" in w for w in res["data_quality_warnings"])

# 11. Outlier Detection Test
def test_outlier_detection():
    dates = pd.date_range("2026-01-01", periods=25, freq="B").strftime("%Y-%m-%d")
    np.random.seed(99)
    p_a = 75000.0 + np.random.normal(0, 10, 25)
    p_b = p_a - 20.0 + np.random.normal(0, 5, 25)
    
    # Inject anomalous bad tick spike on day 18
    p_a[18] += 800.0  # +₹800/10g jump
    
    df_a = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": p_a,
        "raw_close": p_a,
        "volume": 500,
        "open_interest": 2000,
        "dte": 30
    })
    df_b = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": p_b,
        "raw_close": p_b,
        "volume": 500,
        "open_interest": 2000,
        "dte": 30
    })
    
    res = calculate_spread_series(df_a, df_b, "GOLDM", "GOLDPETAL", lookback=10)
    assert any("Outlier observation detected" in w for w in res["data_quality_warnings"])

# 12. Strict Prevention of Look-Ahead Bias Test
def test_prevention_of_look_ahead_bias():
    dates = pd.date_range("2026-01-01", periods=50, freq="B").strftime("%Y-%m-%d")
    np.random.seed(77)
    base = 75000.0 + np.cumsum(np.random.normal(0, 50, 50))
    spread = 15.0 + np.sin(np.linspace(0, 10, 50)) * 30.0
    p_a = base + spread / 2.0
    p_b = base - spread / 2.0
    
    df_a = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": p_a,
        "raw_close": p_a,
        "volume": 1000,
        "open_interest": 5000,
        "dte": 40
    })
    df_b = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": p_b,
        "raw_close": p_b,
        "volume": 1000,
        "open_interest": 5000,
        "dte": 40
    })
    
    # 1. Full 50-day calculation
    full_res = calculate_spread_series(df_a, df_b, "GOLDM", "GOLDPETAL", lookback=15)
    t25_full = full_res["series"][24]  # Row 25 (0-indexed 24)
    
    # 2. Truncated 25-day calculation (Strictly no future dates 26..50 available)
    trunc_a = df_a.iloc[:25].copy()
    trunc_b = df_b.iloc[:25].copy()
    trunc_res = calculate_spread_series(trunc_a, trunc_b, "GOLDM", "GOLDPETAL", lookback=15)
    t25_trunc = trunc_res["series"][24]
    
    # Assert exact point-in-time equivalence
    assert t25_full["trade_date"] == t25_trunc["trade_date"]
    assert np.isclose(t25_full["spread"], t25_trunc["spread"], atol=1e-5)
    assert np.isclose(t25_full["rolling_mean"], t25_trunc["rolling_mean"], atol=1e-5)
    assert np.isclose(t25_full["z_score"], t25_trunc["z_score"], atol=1e-5)
    
    # 3. Corrupt future data at day 40 with extreme values
    corrupted_a = df_a.copy()
    corrupted_a.loc[39, "normalized_close_10g"] = 999999.0
    corrupted_b = df_b.copy()
    corrupted_b.loc[39, "normalized_close_10g"] = 111111.0
    
    corrupt_res = calculate_spread_series(corrupted_a, corrupted_b, "GOLDM", "GOLDPETAL", lookback=15)
    t25_corrupt = corrupt_res["series"][24]
    
    # Day 25 metrics MUST remain 100% untouched by future corruption
    assert np.isclose(t25_full["z_score"], t25_corrupt["z_score"], atol=1e-5)
    assert np.isclose(t25_full["rolling_mean"], t25_corrupt["rolling_mean"], atol=1e-5)

# 13. Distinguishing Observed Spread from Executable Edge Test
def test_friction_bound_divergence_labeled_no_actionable_signal():
    dates = pd.date_range("2026-01-01", periods=20, freq="B").strftime("%Y-%m-%d")
    # Low variance series with small spread (~₹10), with gentle day-to-day drift (not stale)
    np.random.seed(11)
    p_b = 75000.0 + np.linspace(0, 15, 20)
    # Spread is ~10 for first 19 days with small variation, then spikes to 18 on day 20
    spread = np.array([10.0 + (i % 2) * 0.4 for i in range(19)] + [18.0])
    p_a = p_b + spread
    
    df_a = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": p_a,
        "raw_close": p_a,
        "volume": 1000,
        "open_interest": 5000,
        "dte": 30
    })
    df_b = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": p_b,
        "raw_close": p_b,
        "volume": 1000,
        "open_interest": 5000,
        "dte": 30
    })
    
    # Force round-trip friction to ₹35.0 (greater than the ₹18.0 observed spread)
    res = calculate_spread_series(
        df_a, df_b, "GOLDM", "GOLDPETAL",
        lookback=15, z_threshold=1.5, friction_per_10g=35.0
    )
    
    sig = res["signal"]
    # Z-score exceeds 1.5, but net executable edge is negative (18 - 35 = -17)
    assert sig["statistical_metrics"]["z_score"] >= 1.5
    assert sig["signal_type"] == "NO_SIGNAL"
    assert "No actionable signal (Friction-bound divergence)" in sig["signal_label"]
    assert sig["is_actionable"] is False
    assert any("insufficient to overcome" in r for r in sig["reasons"])

# 14. Thin Trading & Unsuitable Expiry Blocking Test
def test_thin_trading_and_unsuitable_expiry_blocking():
    dates = pd.date_range("2026-01-01", periods=20, freq="B").strftime("%Y-%m-%d")
    df_a = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": np.linspace(74000, 75000, 20),
        "raw_close": np.linspace(74000, 75000, 20),
        "volume": [100] * 19 + [2],  # Thin trading on latest session: 2 lots
        "open_interest": 5000,
        "dte": 30
    })
    df_b = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": np.linspace(74000, 74900, 20),
        "raw_close": np.linspace(74000, 74900, 20),
        "volume": 1000,
        "open_interest": 5000,
        "dte": 30
    })
    
    res = calculate_spread_series(df_a, df_b, "GOLDM", "GOLDPETAL", lookback=10)
    assert any("Thin trading in GOLDM" in w for w in res["data_quality_warnings"])
    assert res["signal"]["signal_type"] == "NO_SIGNAL"
    assert res["signal"]["is_actionable"] is False
    assert any("Thin trading" in r for r in res["signal"]["reasons"])

# 15. Compliance Disclaimer Verification Test
def test_compliance_disclaimer_presence():
    dates = pd.date_range("2026-01-01", periods=20, freq="B").strftime("%Y-%m-%d")
    df_a = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": [75000.0] * 20,
        "raw_close": [75000.0] * 20,
        "volume": 500,
        "open_interest": 2000,
        "dte": 30
    })
    df_b = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": [75050.0] * 20,
        "raw_close": [75050.0] * 20,
        "volume": 500,
        "open_interest": 2000,
        "dte": 30
    })
    
    res = calculate_spread_series(df_a, df_b, "GOLDM", "GOLDPETAL", lookback=10)
    disclaimer = res["disclaimer"]
    assert "ANALYTICAL INFORMATION ONLY" in disclaimer
    assert "NOT A GUARANTEED TRADE RECOMMENDATION" in disclaimer
    assert "do not guarantee price convergence" in disclaimer or "does not guarantee" in disclaimer

# 16. Walk-Forward Chronological Isolation & Parameter Freezing Test
def test_walk_forward_chronological_isolation():
    dates = pd.date_range("2026-01-01", periods=60, freq="B").strftime("%Y-%m-%d").tolist()
    np.random.seed(42)
    spread = np.sin(np.linspace(0, 8 * np.pi, 60)) * 40.0
    p_a = 75000.0 + spread / 2.0
    p_b = 75000.0 - spread / 2.0
    
    df_a = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": p_a,
        "volume": 2000,
        "open_interest": 8000,
        "dte": 45
    })
    df_b = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": p_b,
        "volume": 2000,
        "open_interest": 8000,
        "dte": 45
    })
    
    res = run_spread_backtest(
        df_a, df_b, "GOLDM", "GOLDPETAL",
        entry_z=1.2, exit_z=0.2, lookback=15,
        dev_ratio=0.5, val_ratio=0.25, test_ratio=0.25
    )
    assert res["success"] is True
    assert "walk_forward_splits" in res
    splits = res["walk_forward_splits"]
    
    dev = splits["development"]
    val = splits["validation"]
    test = splits["unseen_test"]
    
    # Strict temporal isolation (Zero Shuffling, strictly ordered)
    assert dev["end_date"] < val["start_date"]
    assert val["end_date"] < test["start_date"]
    
    # Parameters must be frozen across all periods
    assert dev["parameters"] == val["parameters"]
    assert val["parameters"] == test["parameters"]
    assert dev["parameters"]["entry_z"] == 1.2
    assert dev["parameters"]["lookback"] == 15

# 17. Walk-Forward Look-Ahead Bias Prevention Test
def test_walk_forward_look_ahead_bias():
    dates = pd.date_range("2026-01-01", periods=60, freq="B").strftime("%Y-%m-%d").tolist()
    np.random.seed(123)
    p_a = 75000.0 + np.sin(np.linspace(0, 6 * np.pi, 60)) * 30.0
    p_b = 75000.0 - np.sin(np.linspace(0, 6 * np.pi, 60)) * 30.0
    
    df_a = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": p_a,
        "volume": 1000,
        "dte": 40
    })
    df_b = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": p_b,
        "volume": 1000,
        "dte": 40
    })
    
    # 1. Baseline simulation
    res_base = run_spread_backtest(df_a, df_b, "GOLDM", "GOLDPETAL", entry_z=1.2, exit_z=0.2, lookback=10)
    dev_base = res_base["walk_forward_splits"]["development"]["metrics"]
    
    # 2. Corrupt future unseen test data (final 15 dates)
    df_a_corrupt = df_a.copy()
    df_b_corrupt = df_b.copy()
    df_a_corrupt.loc[45:, "normalized_close_10g"] = 999999.0
    df_b_corrupt.loc[45:, "normalized_close_10g"] = 111111.0
    
    res_corrupt = run_spread_backtest(df_a_corrupt, df_b_corrupt, "GOLDM", "GOLDPETAL", entry_z=1.2, exit_z=0.2, lookback=10)
    dev_corrupt = res_corrupt["walk_forward_splits"]["development"]["metrics"]
    
    # In-Sample Development performance must be 100% UNCHANGED by future data corruption
    assert np.isclose(dev_base["total_net_pnl"], dev_corrupt["total_net_pnl"], atol=1e-4)
    assert np.isclose(dev_base["total_return_pct"], dev_corrupt["total_return_pct"], atol=1e-4)
    assert dev_base["total_trades"] == dev_corrupt["total_trades"]

# 18. Actual Contract Rolls & Expiry Lifecycle Handling Test
def test_contract_rolls_and_expiry_handling():
    # Multi-expiry scenario over 40 days:
    # Expiry 1: Expiring in near-term (DTE starts at 10 and decreases to 1)
    # Expiry 2: Far-month contract (DTE starts at 70 and decreases to 61)
    dates = pd.date_range("2026-09-01", periods=40, freq="B").strftime("%Y-%m-%d").tolist()
    
    records_a = []
    records_b = []
    
    for idx, d in enumerate(dates):
        dte_near = max(1, 20 - idx)
        dte_far = 80 - idx
        
        # Near contract
        records_a.append({
            "trade_date": d,
            "expiry_date": "2026-09-25",
            "dte": dte_near,
            "normalized_close_10g": 75000.0 + (30.0 if idx < 10 else -10.0),
            "volume": 500
        })
        records_b.append({
            "trade_date": d,
            "expiry_date": "2026-09-25",
            "dte": dte_near,
            "normalized_close_10g": 74950.0,
            "volume": 500
        })
        
        # Far contract (available for roll)
        records_a.append({
            "trade_date": d,
            "expiry_date": "2026-11-25",
            "dte": dte_far,
            "normalized_close_10g": 75200.0,
            "volume": 1000
        })
        records_b.append({
            "trade_date": d,
            "expiry_date": "2026-11-25",
            "dte": dte_far,
            "normalized_close_10g": 75150.0,
            "volume": 1000
        })
        
    df_a = pd.DataFrame(records_a)
    df_b = pd.DataFrame(records_b)
    
    res = run_spread_backtest(
        df_a, df_b, "GOLDM", "GOLDPETAL",
        entry_z=1.0, exit_z=0.2, lookback=10, expiry_buffer_days=3
    )
    assert res["success"] is True
    trades = res["trades"]
    
    # Verify that trades track specific contracts and model expiry events
    assert len(trades) > 0
    # Every trade must have valid contract identifiers and expiry dates
    for t in trades:
        assert t["contract_a"] == "GOLDM"
        assert t["contract_b"] == "GOLDPETAL"
        assert t["expiry_a"] in ["2026-09-25", "2026-11-25"]
    
    # Check that contract roll or expiry exit was logged when near contract expired
    has_expiry_event = any(
        "Contract Expiry Roll" in t["exit_reason"] or "Mandatory Expiry Exit" in t["exit_reason"]
        or t.get("was_rolled") is True
        for t in trades
    )
    assert has_expiry_event

# 19. Transaction Costs Accounting Test
def test_walk_forward_transaction_cost_accounting():
    notional = 1000000.0
    cost_buy = calculate_mcx_trade_cost(notional, is_buy=True)
    cost_sell = calculate_mcx_trade_cost(notional, is_buy=False)
    
    # Sell side has CTT (0.01%), buy side has Stamp Duty (0.002%)
    # At ₹1,000,000 notional: CTT = ₹100, Stamp = ₹20
    assert np.isclose(cost_sell - cost_buy, 80.0, atol=1e-5)
    assert cost_buy > 0.0

# 20. Insufficient Data Rejection Test
def test_insufficient_data_rejection():
    # Only 12 dates provided (fewer than minimum 30 required for 3-phase walk-forward)
    dates = pd.date_range("2026-01-01", periods=12, freq="B").strftime("%Y-%m-%d")
    df_a = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": [75000.0] * 12,
        "volume": 500,
        "dte": 20
    })
    df_b = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": [75020.0] * 12,
        "volume": 500,
        "dte": 20
    })
    
    res = run_spread_backtest(df_a, df_b, "GOLDM", "GOLDPETAL")
    assert res["success"] is False
    assert "Insufficient data for reliable validation" in res["message"]
    assert res["metrics"] is None
    assert res["walk_forward_splits"] is None

# 21. Benchmark Comparison (Alpha & Beta) Test
def test_benchmark_comparison_alpha_beta():
    dates = pd.date_range("2026-01-01", periods=45, freq="B").strftime("%Y-%m-%d").tolist()
    np.random.seed(55)
    bench_price = 75000.0 + np.cumsum(np.random.normal(50, 80, 45))
    spread = np.sin(np.linspace(0, 4 * np.pi, 45)) * 30.0
    
    df_a = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": bench_price + spread / 2.0,
        "volume": 1000,
        "dte": 30
    })
    df_b = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": bench_price - spread / 2.0,
        "volume": 1000,
        "dte": 30
    })
    df_bench = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": bench_price,
        "close": bench_price
    })
    
    res = run_spread_backtest(
        df_a, df_b, "GOLDM", "GOLDPETAL",
        entry_z=1.0, exit_z=0.2, lookback=10,
        benchmark_df=df_bench
    )
    assert res["success"] is True
    bc = res["benchmark_comparison"]
    assert "benchmark_name" in bc
    assert "alpha_pct" in bc
    assert "beta" in bc
    assert "correlation" in bc
    # Alpha = Strategy Return - Benchmark Return
    assert np.isclose(bc["alpha_pct"], bc["strategy_return_pct"] - bc["benchmark_return_pct"], atol=0.05)

# 22. Downloadable Backtest Audit Report Generation Test
def test_downloadable_backtest_report_csv():
    from app.backtesting.engine import generate_backtest_report_csv
    dates = pd.date_range("2026-01-01", periods=45, freq="B").strftime("%Y-%m-%d").tolist()
    df_a = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": 75000.0 + np.sin(np.linspace(0, 4 * np.pi, 45)) * 25.0,
        "volume": 1000,
        "dte": 30
    })
    df_b = pd.DataFrame({
        "trade_date": dates,
        "normalized_close_10g": 75000.0 - np.sin(np.linspace(0, 4 * np.pi, 45)) * 25.0,
        "volume": 1000,
        "dte": 30
    })
    
    res = run_spread_backtest(df_a, df_b, "GOLDM", "GOLDPETAL", entry_z=1.0, exit_z=0.2, lookback=10)
    csv_report = generate_backtest_report_csv(res)
    
    assert "STRATEGY SPECIFICATION & FROZEN PARAMETERS" in csv_report
    assert "CHRONOLOGICAL WALK-FORWARD PARTITIONS" in csv_report
    assert "REGULATORY FRICTION & SLIPPAGE ASSUMPTIONS" in csv_report
    assert "BENCHMARK COMPARISON" in csv_report
    assert "CHRONOLOGICAL TRADE EXECUTION LOG" in csv_report
    assert "LIMITATION DISCLOSURE" in csv_report


