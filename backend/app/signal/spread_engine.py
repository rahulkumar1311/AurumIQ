"""
AurumIQ Relative-Value Analytics & Spread Engine
Problem Statement #03: Commodity Derivatives Intelligence

Features:
- Select two eligible contracts and their specific expiry dates.
- Plot normalized settlement prices and their relative spread over time.
- Calculate percentage premium/discount and rolling z-scores using ONLY information available
  up to each historical date (Strict Zero Look-Ahead Bias).
- Configurable lookback period, signal entry threshold (z-score), and exit threshold.
- Requires sufficient valid historical observations before generating a signal.
- Flags missing data, stale observations, thin trading, and unsuitable expiry combinations.
- Distinguishes observed pricing differences from estimated executable trading opportunities
  (accounting for transaction friction, CTT, GST, stamp duty, bid-ask slippage, and calendar carry).
- Displays exact diagnostic reasoning, reference prices, timestamps, and data-quality warnings.
- Returns "No actionable signal" when thresholds or data-quality requirements are not met.
- Compliance disclaimer: Statistical mispricing does not guarantee arbitrage or convergence.
"""
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from datetime import datetime


def estimate_round_trip_friction(symbol_a: str, symbol_b: str, avg_price_10g: float = 75000.0) -> float:
    """
    Estimates conservative two-leg round-trip transaction friction in INR per 10 grams:
    1. MCX Exchange Turnover Fees: 0.0021% on turn (~₹3.15 per leg)
    2. CTT (Commodity Transaction Tax): 0.01% on sell side (~₹7.50 per leg)
    3. Stamp Duty: 0.002% on buy side (~₹1.50 per leg)
    4. GST: 18% on exchange and broker charges (~₹1.20)
    5. Bid-Ask Spread & Liquidity Slippage:
       - GOLDM / GOLDTEN: ~₹4 to ₹5 / 10g
       - GOLDGUINEA: ~₹8 / 10g
       - GOLDPETAL: ~₹15 / 10g (retail packaging & delivery friction)
    """
    slippage_map = {
        "GOLDM": 4.0,
        "GOLDTEN": 5.0,
        "GOLDGUINEA": 8.0,
        "GOLDPETAL": 15.0
    }
    
    # Statutory regulatory fees per 10g at reference price
    # Buy leg: Turnover (0.0021%) + Stamp (0.002%) + GST
    # Sell leg: Turnover (0.0021%) + CTT (0.01%) + GST
    statutory_per_contract = avg_price_10g * (0.0021 * 2 + 0.01 + 0.002) / 100.0
    statutory_two_legs = statutory_per_contract * 2.0  # Leg A and Leg B
    
    slippage_a = slippage_map.get(symbol_a, 5.0)
    slippage_b = slippage_map.get(symbol_b, 5.0)
    
    total_friction = statutory_two_legs + slippage_a + slippage_b
    return round(float(total_friction), 2)


def calculate_spread_series(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    symbol_a: str,
    symbol_b: str,
    lookback: int = 20,
    use_purity_adjusted: bool = False,
    annual_financing_rate: float = 0.065,  # 6.5% standard Indian repo/financing carry rate
    z_threshold: float = 2.0,
    exit_threshold: float = 0.5,
    min_observations: int = 10,
    friction_per_10g: Optional[float] = None
) -> Dict[str, Any]:
    """
    Computes point-in-time relative-value analytics between two contracts.
    Strictly prevents look-ahead bias by calculating all rolling metrics using only
    prior and current observations.
    """
    if df_a.empty or df_b.empty:
        return {
            "series": [],
            "statistics": None,
            "data_quality_warnings": ["One or both contract datasets are empty."],
            "signal": {
                "signal_type": "NO_SIGNAL",
                "signal_label": "No actionable signal",
                "is_actionable": False,
                "reasons": ["Insufficient data: One or both contract series contain 0 records."]
            },
            "message": "Insufficient data to compute spread series"
        }

    price_col = "purity_adjusted_10g" if use_purity_adjusted else "normalized_close_10g"

    def _get_series(df: pd.DataFrame, preferred: str, alt_list: List[str], default_val: float = 0.0) -> pd.Series:
        if preferred in df.columns:
            return pd.to_numeric(df[preferred], errors="coerce").fillna(default_val)
        for alt in alt_list:
            if alt in df.columns:
                return pd.to_numeric(df[alt], errors="coerce").fillna(default_val)
        return pd.Series(default_val, index=df.index, dtype=float)
