"""
AurumIQ Contract Normalization Engine Unit Tests
Problem Statement #03: Commodity Derivatives Intelligence

Includes hand-calculated examples, quotation-base neutrality proofs,
trading vs quotation unit separation, expiry carry accounting,
and GOLDTEN 2025 listing period handling.
"""
import pytest
from datetime import datetime
import pandas as pd
import numpy as np
from app.normalization.normalizer import ContractNormalizationEngine
from app.config import (
    CONTRACT_SPECS,
    NormalizationConfig,
    DEFAULT_NORMALIZATION_CONFIG
)
from app.signal.spread_engine import calculate_spread_series

# 1. Hand-Calculated Example: Quotation Base Scaling & Purity Factors
def test_hand_calculated_normalization_factors():
    engine = ContractNormalizationEngine()

    # 1. GOLDM: 100g trading unit, 10g quote unit, 995 purity
    m_factors = engine.get_factors("GOLDM")
    assert m_factors["trading_unit_grams"] == 100.0
    assert m_factors["quote_unit_grams"] == 10.0
    assert m_factors["contract_purity"] == 995.0
    assert m_factors["quotation_multiplier"] == 1.0  # 10 / 10
    # Purity multiplier to 999: 999 / 995 ≈ 1.0040201
    assert round(m_factors["purity_multiplier"], 6) == round(999.0 / 995.0, 6)
    assert round(m_factors["composite_multiplier"], 6) == round(1.0 * (999.0 / 995.0), 6)
    assert m_factors["notional_multiplier"] == 10.0  # 100g / 10g

    # 2. GOLDTEN: 10g trading unit, 10g quote unit, 999 purity
    ten_factors = engine.get_factors("GOLDTEN")
    assert ten_factors["trading_unit_grams"] == 10.0
    assert ten_factors["quote_unit_grams"] == 10.0
    assert ten_factors["contract_purity"] == 999.0
    assert ten_factors["quotation_multiplier"] == 1.0  # 10 / 10
    assert ten_factors["purity_multiplier"] == 1.0     # 999 / 999
    assert ten_factors["composite_multiplier"] == 1.0
    assert ten_factors["notional_multiplier"] == 1.0   # 10g / 10g

    # 3. GOLDGUINEA: 8g trading unit, 8g quote unit, 995 official purity
    guinea_factors = engine.get_factors("GOLDGUINEA")
    assert guinea_factors["trading_unit_grams"] == 8.0
    assert guinea_factors["quote_unit_grams"] == 8.0
    assert guinea_factors["contract_purity"] == 995.0
    assert guinea_factors["official_mcx_purity"] == 995.0
    assert guinea_factors["problem_statement_purity"] == 999.0
    assert guinea_factors["is_flagged_assumption"] is True
    assert guinea_factors["quotation_multiplier"] == 1.25  # 10 / 8
    assert guinea_factors["purity_multiplier"] == pytest.approx(999.0 / 995.0)
    assert guinea_factors["composite_multiplier"] == pytest.approx(1.25 * (999.0 / 995.0))
    assert guinea_factors["notional_multiplier"] == 1.0    # 8g / 8g

    # Test under PROBLEM_STATEMENT_03 convention
    engine_ps = ContractNormalizationEngine(NormalizationConfig(purity_convention="PROBLEM_STATEMENT_03"))
    guinea_ps = engine_ps.get_factors("GOLDGUINEA")
    assert guinea_ps["contract_purity"] == 999.0
    assert guinea_ps["purity_multiplier"] == 1.0
    assert guinea_ps["composite_multiplier"] == 1.25

    # 4. GOLDPETAL: 1g trading unit, 1g quote unit, 999 purity
    petal_factors = engine.get_factors("GOLDPETAL")
    assert petal_factors["trading_unit_grams"] == 1.0
    assert petal_factors["quote_unit_grams"] == 1.0
    assert petal_factors["contract_purity"] == 999.0
    assert petal_factors["quotation_multiplier"] == 10.0  # 10 / 1
    assert petal_factors["purity_multiplier"] == 1.0      # 999 / 999
    assert petal_factors["composite_multiplier"] == 10.0
    assert petal_factors["notional_multiplier"] == 1.0    # 1g / 1g

# 2. Proof: Quotation-Base Differences Alone DO NOT Create False Pricing Signals
def test_quotation_base_neutrality_proof():
    """
    Mathematical Proof:
    Suppose physical gold is valued at exactly ₹7,500.00 per gram.
    Raw settlement prices on exchange will be:
      - GOLDTEN:   10g * ₹7,500 = ₹75,000.00 (quoted per 10g)
      - GOLDGUINEA: 8g * ₹7,500 = ₹60,000.00 (quoted per 8g)
      - GOLDPETAL:  1g * ₹7,500 = ₹7,500.00  (quoted per 1g)
    On the standardized nominal 10g quotation base (normalized_close_10g),
    all three MUST yield precisely ₹75,000.00 / 10g with 0.00 spread.
    """
    engine = ContractNormalizationEngine()
    t_date = "2026-09-15"
    e_date = "2026-10-05"

    ten_rec = {
        "symbol": "GOLDTEN",
        "trade_date": t_date,
        "expiry_date": e_date,
        "close": 75000.0,
        "open": 75000.0, "high": 75000.0, "low": 75000.0
    }
    guinea_rec = {
        "symbol": "GOLDGUINEA",
        "trade_date": t_date,
        "expiry_date": e_date,
        "close": 60000.0,
        "open": 60000.0, "high": 60000.0, "low": 60000.0
    }
    petal_rec = {
        "symbol": "GOLDPETAL",
        "trade_date": t_date,
        "expiry_date": e_date,
        "close": 7500.0,
        "open": 7500.0, "high": 7500.0, "low": 7500.0
    }

    norm_ten = engine.normalize_single_record(ten_rec)
    norm_guinea = engine.normalize_single_record(guinea_rec)
    norm_petal = engine.normalize_single_record(petal_rec)

    # All three must normalize to exactly ₹75,000.00 on nominal 10g quotation base
    assert norm_ten["normalized_close_10g"] == 75000.0
    assert norm_guinea["normalized_close_10g"] == 75000.0
    assert norm_petal["normalized_close_10g"] == 75000.0

    # Spreads between any combination on nominal 10g base must be zero
    spread_ten_petal = norm_ten["normalized_close_10g"] - norm_petal["normalized_close_10g"]
    spread_ten_guinea = norm_ten["normalized_close_10g"] - norm_guinea["normalized_close_10g"]
    spread_guinea_petal = norm_guinea["normalized_close_10g"] - norm_petal["normalized_close_10g"]
    assert spread_ten_petal == 0.0
    assert spread_ten_guinea == 0.0
    assert spread_guinea_petal == 0.0

    # Under PROBLEM_STATEMENT_03 convention, fine-gold equivalent is also identical
    engine_ps = ContractNormalizationEngine(NormalizationConfig(purity_convention="PROBLEM_STATEMENT_03"))
    ps_guinea = engine_ps.normalize_single_record(guinea_rec)
    assert ps_guinea["purity_adjusted_10g"] == 75000.0

    assert abs(spread_ten_petal) < 1e-6
    assert abs(spread_ten_guinea) < 1e-6
    assert abs(spread_guinea_petal) < 1e-6

# 3. Separation of Trading Unit and Quotation Unit Notional Value
def test_trading_vs_quotation_unit_separation():
    engine = ContractNormalizationEngine()
    t_date = "2026-09-15"
    e_date = "2026-10-05"

    # GOLDM: Quoted ₹75,000 per 10g, but trading lot is 100g!
    # Notional contract value = 75,000 * (100 / 10) = ₹750,000.00
    goldm_rec = {
        "symbol": "GOLDM",
        "trade_date": t_date,
        "expiry_date": e_date,
        "close": 75000.0
    }
    norm_goldm = engine.normalize_single_record(goldm_rec)
    assert norm_goldm["trading_unit_grams"] == 100.0
    assert norm_goldm["quote_unit_grams"] == 10.0
    assert norm_goldm["contract_notional_inr"] == 750000.0

    # GOLDTEN: Quoted ₹75,000 per 10g, trading lot is 10g
    # Notional contract value = 75,000 * (10 / 10) = ₹75,000.00
    goldten_rec = {
        "symbol": "GOLDTEN",
        "trade_date": t_date,
        "expiry_date": e_date,
        "close": 75000.0
    }
    norm_ten = engine.normalize_single_record(goldten_rec)
    assert norm_ten["trading_unit_grams"] == 10.0
    assert norm_ten["quote_unit_grams"] == 10.0
    assert norm_ten["contract_notional_inr"] == 75000.0

# 4. Preservation of Original Exchange Settlement Prices
def test_preserves_original_exchange_prices():
    engine = ContractNormalizationEngine()
    petal_rec = {
        "symbol": "GOLDPETAL",
        "trade_date": "2026-09-15",
        "expiry_date": "2026-10-05",
        "open": 7480.0,
        "high": 7530.0,
        "low": 7475.0,
        "close": 7510.0,
        "volume": 2500,
        "open_interest": 8000
    }
    norm = engine.normalize_single_record(petal_rec)

    # Raw prices strictly preserved
    assert norm["raw_close"] == 7510.0
    assert norm["raw_open"] == 7480.0
    assert norm["raw_high"] == 7530.0
    assert norm["raw_low"] == 7475.0

    # Analytical standardized prices calculated alongside
    assert norm["normalized_close_10g"] == 75100.0  # 7510 * 10
    assert norm["purity_adjusted_10g"] == 75100.0   # 999/999 = 1.0

# 5. Expiry Alignment and Calendar Carry Accounting
def test_expiry_carry_drag_accounting():
    """
    Tests that comparing contracts with different expiries accounts for maturity carry drag
    rather than treating them as identical instruments.
    """
    dates = pd.date_range("2026-01-01", periods=20, freq="B").strftime("%Y-%m-%d")
    
    # Contract A: Far expiry (DTE = 90 days)
    # Contract B: Near expiry (DTE = 30 days)
    # Net DTE diff = 60 days
    df_a = pd.DataFrame({
        "trade_date": dates,
        "expiry_date": ["2026-04-05"] * 20,
        "purity_adjusted_10g": [75800.0] * 20,
        "volume": [1000] * 20,
        "open_interest": [5000] * 20,
        "dte": [90] * 20
    })
    df_b = pd.DataFrame({
        "trade_date": dates,
        "expiry_date": ["2026-02-05"] * 20,
        "purity_adjusted_10g": [75000.0] * 20,
        "volume": [1000] * 20,
        "open_interest": [5000] * 20,
        "dte": [30] * 20
    })

    res = calculate_spread_series(df_a, df_b, "GOLDM", "GOLDM", lookback=10)
    assert res["message"] == "Success"
    stats = res["statistics"]

    # Verify that different expiries were detected
    assert stats["is_matched_expiry"] is False
    assert stats["expiry_status"] == "CALENDAR_SPREAD_DIFFERENTIAL"
    assert stats["latest_dte_diff"] == 60  # 90 - 30

    # Theoretical carry drag: Price_B * 6.5% * (60 / 365) = 75000 * 0.065 * 60 / 365 ≈ ₹801.37
    expected_carry = round(75000.0 * 0.065 * (60.0 / 365.0), 2)
    assert round(stats["latest_carry_drag"], 2) == expected_carry

    # Maturity-adjusted spread = Gross Spread (800) - Carry Drag (~801.37) ≈ -₹1.37
    expected_adj_spread = round(800.0 - expected_carry, 2)
    assert round(stats["latest_maturity_adjusted_spread"], 2) == expected_adj_spread

# 6. Handling GOLDTEN Shorter History (No Fabricated Pre-Listing Data)
def test_goldten_shorter_history_handling():
    """
    Tests that GOLDTEN's missing observations before its listing date are handled
    gracefully without fabricating synthetic prior data.
    """
    # GOLDM has 30 days of data (Day 1 to 30)
    # GOLDTEN has data only from Day 16 to 30 (listing date Day 16)
    all_dates = pd.date_range("2026-05-01", periods=30, freq="B").strftime("%Y-%m-%d")
    goldten_dates = all_dates[15:]  # Only last 15 days

    df_goldm = pd.DataFrame({
        "trade_date": all_dates,
        "expiry_date": ["2026-10-05"] * 30,
        "purity_adjusted_10g": [75000.0 + i * 5 for i in range(30)],
        "volume": [1000] * 30,
        "open_interest": [5000] * 30,
        "dte": [30] * 30
    })

    df_goldten = pd.DataFrame({
        "trade_date": goldten_dates,
        "expiry_date": ["2026-10-05"] * 15,
        "purity_adjusted_10g": [75000.0 + i * 5 for i in range(15)],
        "volume": [500] * 15,
        "open_interest": [2000] * 15,
        "dte": [30] * 15
    })

    res = calculate_spread_series(df_goldm, df_goldten, "GOLDM", "GOLDTEN", lookback=10)
    assert res["message"] == "Success"
    
    # Overlap must be strictly 15 days, NOT 30 days (no fabricated data)
    assert len(res["series"]) == 15
    assert res["statistics"]["sample_size"] == 15
    assert res["statistics"]["history_note"] is not None
    assert "2025" in res["statistics"]["history_note"]

# 7. Assumptions Report Audit Generation
def test_assumptions_report_generation():
    engine = ContractNormalizationEngine()
    report = engine.get_assumptions_report()

    assert "reference_standard" in report
    assert report["reference_standard"]["weight_grams"] == 10.0
    assert report["reference_standard"]["purity_fineness"] == 999.0
    assert len(report["contract_factors"]) == 4
    assert "mathematical_formulas" in report
