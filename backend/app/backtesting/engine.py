"""
AurumIQ Defensible Walk-Forward Backtesting Engine
Commodity Derivatives Intelligence — Multi-Contract MCX Gold Quantitative Analytics

Key Architectural Features:
1. Strict Chronological Walk-Forward Partitioning:
   - Splits historical observations chronologically into Development (In-Sample / Train),
     Validation (Calibration / Selection), and Final Unseen Test (Out-of-Sample / Test).
   - Zero random shuffling or forward lookahead.
2. Frozen In-Sample Parameter Calibration:
   - Signal parameters fitted/calibrated solely on the Development window and strictly frozen
     before evaluating the Validation and Unseen Test periods.
3. Actual Individual Contract & Expiry Lifecycle Modeling:
   - Models physical positions in specific contract expiries (e.g. GOLDM Oct-26 and GOLDPETAL Oct-26).
   - Avoids artificial continuous near-month series that hide roll price gaps and tender costs.
   - Enforces contract lifecycle rules: closes or rolls positions prior to delivery tender buffer (DTE <= buffer).
4. Realistic MCX Microstructure & Regulatory Friction:
   - Exact statutory costs: MCX turnover charges (0.0021%), CTT (0.01% on sell side only),
     Stamp Duty (0.002% on buy side only), Brokerage (0.005%), GST (18% on fees).
   - Contract-specific bid-ask slippage (e.g. ₹4/10g for GOLDM, ₹15/10g for GOLDPETAL).
   - Clear disclosure of settlement price limitations and illiquid print execution penalties.
5. Benchmark & Alpha Comparison:
   - Benchmarks strategy performance against Buy & Hold MCX Gold Underlying to distinguish
     relative-value alpha from passive gold market beta.
6. Comprehensive Walk-Forward Reporting:
   - Gross/Net PnL, Turnover, Itemized Friction, Drawdown, Trade Count, Alpha, Beta, Sharpe,
     and out-of-sample degradation metrics.
   - Displays "Insufficient data for reliable validation" when sample size is insufficient.
"""
from typing import Dict, Any, List, Optional, Tuple
import uuid
import numpy as np
import pandas as pd
from app.config import (
    MCX_TURNOVER_FEE_PCT,
    CTT_SELL_PCT,
    STAMP_DUTY_BUY_PCT,
    BROKERAGE_PCT,
    GST_PCT,
    CONTRACT_SPECS
)

# Standard contract slippage per 10 grams benchmark (INR)
DEFAULT_SLIPPAGE_MAP: Dict[str, float] = {
    "GOLDM": 4.0,
    "GOLDTEN": 5.0,
    "GOLDGUINEA": 8.0,
    "GOLDPETAL": 15.0
}

SETTLEMENT_PRICE_LIMITATION_DISCLOSURE = (
    "LIMITATION DISCLOSURE: Daily settlement prices represent official exchange closing clearing marks, "
    "not guaranteed trade execution fills. In live markets, fill prices are subject to order book depth, "
    "bid-ask spreads, and execution slippage. In thin retail contracts (GOLDGUINEA, GOLDPETAL), "
    "illiquidity fill surcharges are modeled."
)

UNKNOWN_COSTS_DISCLOSURE = {
    "physical_delivery_tender_penalty": 0.0,
    "vaulting_and_assaying_charges": 0.0,
    "variation_margin_financing_rate": "Configurable (assumed 0% for fully collateralized margin)",
    "notes": "Physical tender penalties are 100% avoided by enforcing mandatory contractual roll prior to tender buffer (DTE <= 3d)."
}


def calculate_mcx_trade_cost(
    notional_turnover: float,
    is_buy: bool,
    brokerage_pct: float = BROKERAGE_PCT,
    exchange_fee_pct: float = MCX_TURNOVER_FEE_PCT,
    ctt_sell_pct: float = CTT_SELL_PCT,
    stamp_duty_buy_pct: float = STAMP_DUTY_BUY_PCT,
    gst_pct: float = GST_PCT
) -> float:
    """
    Computes exact regulatory transaction cost for an MCX futures transaction in INR.
    - CTT is charged strictly on the sell side (0.01%).
    - Stamp Duty is charged strictly on the buy side (0.002%).
    - GST is 18% on (Brokerage + Exchange Fees).
    """
    brokerage = notional_turnover * (brokerage_pct / 100.0)
    exchange_fee = notional_turnover * (exchange_fee_pct / 100.0)
    gst = (brokerage + exchange_fee) * (gst_pct / 100.0)
    
    ctt = notional_turnover * (ctt_sell_pct / 100.0) if not is_buy else 0.0
    stamp_duty = notional_turnover * (stamp_duty_buy_pct / 100.0) if is_buy else 0.0
    
    return float(brokerage + exchange_fee + gst + ctt + stamp_duty)


def calculate_leg_friction(
    symbol: str,
    price_10g: float,
    units_10g: float,
    is_buy: bool,
    volume: int = 100,
    slippage_map: Optional[Dict[str, float]] = None,
    include_friction: bool = True
) -> Dict[str, float]:
    """
    Calculates detailed itemized friction for a single leg execution.
    """
    if not include_friction:
        return {
            "brokerage": 0.0,
            "exchange_fee": 0.0,
            "gst": 0.0,
            "ctt": 0.0,
            "stamp_duty": 0.0,
            "slippage": 0.0,
            "total_friction": 0.0
        }
        
    notional = float(price_10g * units_10g)
    brokerage = notional * (BROKERAGE_PCT / 100.0)
    exchange_fee = notional * (MCX_TURNOVER_FEE_PCT / 100.0)
    gst = (brokerage + exchange_fee) * (GST_PCT / 100.0)
    ctt = notional * (CTT_SELL_PCT / 100.0) if not is_buy else 0.0
    stamp_duty = notional * (STAMP_DUTY_BUY_PCT / 100.0) if is_buy else 0.0
    
    s_map = slippage_map or DEFAULT_SLIPPAGE_MAP
    base_slip = s_map.get(symbol, 5.0)
    
    # Illiquidity surcharge: If trading volume is thin (< 10 lots), apply 1.5x slippage penalty
    slip_multiplier = 1.5 if volume < 10 else 1.0
    slippage = base_slip * slip_multiplier * units_10g
    
    total = brokerage + exchange_fee + gst + ctt + stamp_duty + slippage
    return {
        "brokerage": round(brokerage, 2),
        "exchange_fee": round(exchange_fee, 2),
        "gst": round(gst, 2),
        "ctt": round(ctt, 2),
        "stamp_duty": round(stamp_duty, 2),
        "slippage": round(slippage, 2),
        "total_friction": round(total, 2)
    }


def compute_performance_metrics(
    trades: List[Dict[str, Any]],
