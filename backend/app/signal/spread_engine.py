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

    raw_close_a = _get_series(df_a, "raw_close", ["close"], 0.0)
    raw_close_b = _get_series(df_b, "raw_close", ["close"], 0.0)

    sub_a = pd.DataFrame({
        "trade_date": df_a["trade_date"].astype(str),
        "price_a": _get_series(df_a, price_col, ["purity_adjusted_10g", "normalized_close_10g", "close", "raw_close"]),
        "raw_close_a": raw_close_a,
        "expiry_a": df_a["expiry_date"].astype(str) if "expiry_date" in df_a.columns else "",
        "volume_a": pd.to_numeric(df_a["volume"], errors="coerce").fillna(0) if "volume" in df_a.columns else 0,
        "oi_a": pd.to_numeric(df_a["open_interest"], errors="coerce").fillna(0) if "open_interest" in df_a.columns else 0,
        "dte_a": pd.to_numeric(df_a["dte"], errors="coerce").fillna(0) if "dte" in df_a.columns else 0,
    })
    sub_b = pd.DataFrame({
        "trade_date": df_b["trade_date"].astype(str),
        "price_b": _get_series(df_b, price_col, ["purity_adjusted_10g", "normalized_close_10g", "close", "raw_close"]),
        "raw_close_b": raw_close_b,
        "expiry_b": df_b["expiry_date"].astype(str) if "expiry_date" in df_b.columns else "",
        "volume_b": pd.to_numeric(df_b["volume"], errors="coerce").fillna(0) if "volume" in df_b.columns else 0,
        "oi_b": pd.to_numeric(df_b["open_interest"], errors="coerce").fillna(0) if "open_interest" in df_b.columns else 0,
        "dte_b": pd.to_numeric(df_b["dte"], errors="coerce").fillna(0) if "dte" in df_b.columns else 0,
    })

    # Merge strictly on trade_date (Inner join ensures overlapping dates only)
    merged = pd.merge(sub_a, sub_b, on="trade_date", how="inner").sort_values("trade_date").reset_index(drop=True)
    
    data_quality_warnings: List[str] = []
    
    if len(merged) < min_observations:
        data_quality_warnings.append(
            f"Insufficient history: Only {len(merged)} overlapping trading dates found. At least {min_observations} required."
        )
        return {
            "series": [],
            "statistics": None,
            "data_quality_warnings": data_quality_warnings,
            "signal": {
                "signal_type": "NO_SIGNAL",
                "signal_label": "No actionable signal",
                "is_actionable": False,
                "reasons": [f"Insufficient historical observations ({len(merged)} available, {min_observations} required)."]
            },
            "message": f"Only {len(merged)} overlapping dates found. At least {min_observations} required."
        }

    # 1. Gross Spread & Percentage Premium/Discount
    merged["spread"] = (merged["price_a"] - merged["price_b"]).round(2)
    merged["pct_spread"] = ((merged["spread"] / merged["price_b"].replace(0, np.nan)) * 100.0).round(3).fillna(0.0)

    # 2. Maturity & Carry Accounting
    merged["is_matched_expiry"] = merged["expiry_a"] == merged["expiry_b"]
    merged["dte_diff"] = (merged["dte_a"] - merged["dte_b"]).astype(int)
    
    # Theoretical calendar carry drag per 10g:
    # Carry Drag = Price_B * r * (DTE_A - DTE_B) / 365
    merged["calendar_carry_drag"] = (
        merged["price_b"] * annual_financing_rate * (merged["dte_diff"] / 365.0)
    ).round(2)
    
    # Maturity-Adjusted Residual Spread = Spread - Calendar Carry Drag
    merged["maturity_adjusted_spread"] = (merged["spread"] - merged["calendar_carry_drag"]).round(2)

    # 3. Estimated Round-Trip Friction & Net Executable Spread
    avg_price = float(merged["price_a"].mean()) if not merged["price_a"].empty else 75000.0
    computed_friction = estimate_round_trip_friction(symbol_a, symbol_b, avg_price) if friction_per_10g is None else friction_per_10g
    merged["estimated_friction"] = computed_friction
    
    # Net Executable Spread: Positive if spread magnitude exceeds friction & carry drag
    merged["net_executable_spread"] = (
        merged["maturity_adjusted_spread"].abs() - computed_friction
    ).round(2)

    # 4. Point-in-Time Rolling Statistics (STRICT ZERO LOOK-AHEAD BIAS)
    # Using window up to current index i without backward filling or forward leakage
    n_rows = len(merged)
    rolling_means = [np.nan] * n_rows
    rolling_stds = [np.nan] * n_rows
    z_scores = [0.0] * n_rows
    valid_z_flags = [False] * n_rows
    zero_variance_flags = [False] * n_rows

    spreads_array = merged["spread"].values
    for i in range(n_rows):
        start_idx = max(0, i - lookback + 1)
        window = spreads_array[start_idx : i + 1]
        
        # Require at least min_observations in current window
        if len(window) >= min_observations:
            m = float(np.mean(window))
            s = float(np.std(window, ddof=1)) if len(window) > 1 else 0.0
            rolling_means[i] = round(m, 2)
            rolling_stds[i] = round(s, 2)
            
            if s < 1e-8:
                # Zero variance (flat spread)
                zero_variance_flags[i] = True
                z_scores[i] = 0.0
                valid_z_flags[i] = False
            else:
                z = (spreads_array[i] - m) / s
                z_scores[i] = round(float(z), 3)
                valid_z_flags[i] = True

    merged["rolling_mean"] = rolling_means
    merged["rolling_std"] = rolling_stds
    merged["z_score"] = z_scores
    merged["valid_z"] = valid_z_flags
    merged["zero_variance"] = zero_variance_flags

    # Bollinger Bands (calculated where rolling mean is available)
    merged["upper_band"] = [
        round(m + z_threshold * s, 2) if not np.isnan(m) and not np.isnan(s) else None
        for m, s in zip(rolling_means, rolling_stds)
    ]
    merged["lower_band"] = [
        round(m - z_threshold * s, 2) if not np.isnan(m) and not np.isnan(s) else None
        for m, s in zip(rolling_means, rolling_stds)
    ]
    merged["upper_1s"] = [
        round(m + 1.0 * s, 2) if not np.isnan(m) and not np.isnan(s) else None
        for m, s in zip(rolling_means, rolling_stds)
    ]
    merged["lower_1s"] = [
        round(m - 1.0 * s, 2) if not np.isnan(m) and not np.isnan(s) else None
        for m, s in zip(rolling_means, rolling_stds)
    ]
    # For backward compatibility
    merged["upper_2s"] = merged["upper_band"]
    merged["lower_2s"] = merged["lower_band"]

    # 5. Data Quality Auditing (Flags missing data, stale observations, thin trading, unsuitable expiries, outliers)
    # Check date gaps (> 4 calendar days)
    trade_dates = pd.to_datetime(merged["trade_date"])
    date_diffs = (trade_dates.diff().dt.days).fillna(1)
    gaps = merged[date_diffs > 4]
    if not gaps.empty:
        for idx, gap_row in gaps.iterrows():
            days_gap = int(date_diffs.loc[idx])
            data_quality_warnings.append(
                f"Missing observations: {days_gap}-day gap in trading dates detected before {gap_row['trade_date']}."
            )

    # Check asymmetric calendar observations (dates in one contract not in another)
    dates_a = set(sub_a["trade_date"])
    dates_b = set(sub_b["trade_date"])
    missing_in_b = dates_a - dates_b
    missing_in_a = dates_b - dates_a
    if missing_in_b:
        data_quality_warnings.append(
            f"Missing observations: {len(missing_in_b)} trading session(s) present in {symbol_a} are missing in {symbol_b}."
        )
    if missing_in_a:
        data_quality_warnings.append(
            f"Missing observations: {len(missing_in_a)} trading session(s) present in {symbol_b} are missing in {symbol_a}."
        )

    # Check stale observations (consecutive identical prices >= 3 days)
    stale_a = (merged["price_a"].diff() == 0) & (merged["price_a"].diff().shift(1) == 0)
    stale_b = (merged["price_b"].diff() == 0) & (merged["price_b"].diff().shift(1) == 0)
    if stale_a.any():
        data_quality_warnings.append(
            f"Stale pricing detected in {symbol_a}: 3 or more consecutive sessions with identical settlement prices."
        )
    if stale_b.any():
        data_quality_warnings.append(
            f"Stale pricing detected in {symbol_b}: 3 or more consecutive sessions with identical settlement prices."
        )

    # Outlier detection: Identify anomalous spread jumps relative to rolling spread volatility (> 3.5 sigma)
    spread_diffs = merged["spread"].diff().abs()
    rolling_diff_std = spread_diffs.rolling(window=min(lookback, 15), min_periods=5).std()
    for idx in range(1, len(merged)):
        s_diff = spread_diffs.iloc[idx]
        local_std = rolling_diff_std.iloc[idx - 1] if idx > 1 else np.nan
        if not np.isnan(local_std) and local_std > 1e-4:
            if s_diff > 3.5 * local_std and s_diff > 25.0:
                outlier_date = merged.iloc[idx]["trade_date"]
                data_quality_warnings.append(
                    f"Outlier observation detected on {outlier_date}: single-session spread change of ₹{s_diff:.2f}/10g exceeds 3.5σ ({s_diff/local_std:.1f}σ). Possible bad tick, auction imbalance, or illiquid print."
                )

    latest = merged.iloc[-1]
    
    # Check thin trading
    is_thin_a = latest["volume_a"] < 5
    is_thin_b = latest["volume_b"] < 5
    if is_thin_a:
        data_quality_warnings.append(
            f"Thin trading in {symbol_a}: Latest trading volume is {int(latest['volume_a'])} lots (below liquidity threshold of 5)."
        )
    if is_thin_b:
        data_quality_warnings.append(
            f"Thin trading in {symbol_b}: Latest trading volume is {int(latest['volume_b'])} lots (below liquidity threshold of 5)."
        )
    if latest["oi_a"] < 10 or latest["oi_b"] < 10:
        data_quality_warnings.append(
            f"Low open interest: {symbol_a} OI={int(latest['oi_a'])}, {symbol_b} OI={int(latest['oi_b'])} contracts."
        )

    # Check unsuitable expiry combinations and tender period constraints
    is_expired = latest["dte_a"] <= 0 or latest["dte_b"] <= 0
    in_tender_period = (latest["dte_a"] <= 3) or (latest["dte_b"] <= 3)
    is_extreme_dte_diff = abs(int(latest["dte_diff"])) > 45

    if is_expired:
        data_quality_warnings.append(
            "Unsuitable expiry: One or both contracts have reached or passed their expiration date (DTE <= 0)."
        )
    elif in_tender_period:
        data_quality_warnings.append(
            f"Physical delivery tender period active: Near contract has DTE <= 3d (Leg A DTE={int(latest['dte_a'])}, "
            f"Leg B DTE={int(latest['dte_b'])}). Under MCX compulsory delivery rules, positions are subject to "
            f"delivery margins and physical allocation. Non-delivery systematic relative-value trading is blocked."
        )

