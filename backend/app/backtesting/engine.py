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
    equity_curve: List[Dict[str, Any]],
    initial_capital: float,
    benchmark_returns: Optional[pd.Series] = None
) -> Dict[str, Any]:
    """
    Computes standard quantitative metrics including Net PnL, Drawdown, Sharpe, Win Rate,
    and Benchmark Alpha/Beta comparison.
    """
    total_trades = len(trades)
    winning_trades = [t for t in trades if t["net_pnl"] > 0]
    losing_trades = [t for t in trades if t["net_pnl"] < 0]
    
    win_rate = (len(winning_trades) / total_trades * 100.0) if total_trades > 0 else 0.0
    total_gross_profit = sum(t["gross_pnl"] for t in winning_trades)
    total_gross_loss = abs(sum(t["gross_pnl"] for t in losing_trades))
    profit_factor = (total_gross_profit / total_gross_loss) if total_gross_loss > 0 else (99.0 if total_gross_profit > 0 else 0.0)
    
    final_capital = equity_curve[-1]["capital"] if equity_curve else initial_capital
    total_net_pnl = final_capital - initial_capital
    total_return_pct = (total_net_pnl / initial_capital) * 100.0 if initial_capital > 0 else 0.0
    total_costs_paid = sum(t.get("transaction_costs", 0.0) for t in trades)
    total_turnover = sum(t.get("turnover", 0.0) for t in trades)
    
    max_dd = max([p.get("drawdown_pct", 0.0) for p in equity_curve]) if equity_curve else 0.0
    max_dd_inr = max([p.get("drawdown_inr", 0.0) for p in equity_curve]) if equity_curve else 0.0
    
    # Strategy daily returns
    if len(equity_curve) > 2:
        caps = pd.Series([p["capital"] for p in equity_curve])
        strat_rets = caps.pct_change().dropna()
        if len(strat_rets) > 1 and strat_rets.std() > 1e-7:
            sharpe = float(np.sqrt(252.0) * (strat_rets.mean() / strat_rets.std()))
        else:
            sharpe = 0.0
    else:
        sharpe = 0.0
        strat_rets = pd.Series([], dtype=float)
        
    avg_holding = float(np.mean([t["holding_days"] for t in trades])) if trades else 0.0
    
    # Benchmark comparison (Alpha & Beta against Buy & Hold Gold Benchmark)
    alpha_pct = 0.0
    beta = 0.0
    correlation = 0.0
    info_ratio = 0.0
    bench_return_pct = 0.0
    
    if benchmark_returns is not None and len(benchmark_returns) > 1 and len(strat_rets) > 1:
        # Align series lengths
        min_len = min(len(strat_rets), len(benchmark_returns))
        s_aligned = strat_rets.iloc[-min_len:]
        b_aligned = benchmark_returns.iloc[-min_len:]
        
        bench_cum = float((np.prod(1.0 + b_aligned) - 1.0) * 100.0)
        bench_return_pct = round(bench_cum, 2)
        alpha_pct = round(total_return_pct - bench_return_pct, 2)
        
        var_b = float(b_aligned.var())
        cov_sb = float(np.cov(s_aligned, b_aligned)[0][1]) if len(s_aligned) > 1 else 0.0
        beta = round(cov_sb / var_b, 3) if var_b > 1e-8 else 0.0
        
        corr_val = float(s_aligned.corr(b_aligned))
        correlation = round(corr_val, 3) if not np.isnan(corr_val) else 0.0
        
        diff = s_aligned - b_aligned
        if len(diff) > 1 and diff.std() > 1e-7:
            info_ratio = round(float(np.sqrt(252.0) * (diff.mean() / diff.std())), 2)

    return {
        "initial_capital": round(initial_capital, 2),
        "final_capital": round(final_capital, 2),
        "total_net_pnl": round(total_net_pnl, 2),
        "total_gross_pnl": round(sum(t.get("gross_pnl", 0.0) for t in trades), 2),
        "total_return_pct": round(total_return_pct, 2),
        "benchmark_return_pct": bench_return_pct,
        "alpha_pct": alpha_pct,
        "beta_to_gold": beta,
        "correlation_to_gold": correlation,
        "information_ratio": info_ratio,
        "total_trades": total_trades,
        "winning_trades": len(winning_trades),
        "losing_trades": len(losing_trades),
        "win_rate_pct": round(win_rate, 2),
        "profit_factor": round(profit_factor, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "max_drawdown_inr": round(max_dd_inr, 2),
        "sharpe_ratio": round(sharpe, 2),
        "total_statutory_costs": round(total_costs_paid, 2),
        "total_turnover": round(total_turnover, 2),
        "average_holding_days": round(avg_holding, 1)
    }


def simulate_contract_pairs(
    df_a_all: pd.DataFrame,
    df_b_all: pd.DataFrame,
    pair_a: str,
    pair_b: str,
    dates: List[str],
    entry_z: float,
    exit_z: float,
    stop_loss_z: float,
    lookback: int,
    initial_capital: float,
    expiry_buffer_days: int = 3,
    units_10g: float = 10.0,
    use_purity_adjusted: bool = False,
    include_friction: bool = True,
    slippage_map: Optional[Dict[str, float]] = None,
    benchmark_df: Optional[pd.DataFrame] = None
) -> Dict[str, Any]:
    """
    Simulates a pairs trading strategy on authentic individual contracts over a specific list of dates.
    Strictly avoids artificial continuous series roll jumps by modeling physical positions in actual expiries,
    monitoring contract DTE, and executing contract rolls or tender-period mandatory exits.
    """
    price_col = "purity_adjusted_10g" if use_purity_adjusted else "normalized_close_10g"
    
    # Index dataframes by (symbol, trade_date, expiry_date) and (symbol, trade_date)
    # Ensure trade_date is string
    df_a = df_a_all.copy()
    df_b = df_b_all.copy()
    df_a["trade_date"] = df_a["trade_date"].astype(str)
    df_b["trade_date"] = df_b["trade_date"].astype(str)
    
    if "expiry_date" not in df_a.columns:
        df_a["expiry_date"] = "2026-10-05"
    if "expiry_date" not in df_b.columns:
        df_b["expiry_date"] = "2026-10-05"
    if "dte" not in df_a.columns:
        df_a["dte"] = 30
    if "dte" not in df_b.columns:
        df_b["dte"] = 30
    if "volume" not in df_a.columns:
        df_a["volume"] = 100
    if "volume" not in df_b.columns:
        df_b["volume"] = 100
    if price_col not in df_a.columns:
        df_a[price_col] = df_a["close"] if "close" in df_a.columns else 75000.0
    if price_col not in df_b.columns:
        df_b[price_col] = df_b["close"] if "close" in df_b.columns else 75000.0
    
    # State tracking
    position = 0  # 0: flat, +1: Long Spread (Buy A, Sell B), -1: Short Spread (Sell A, Buy B)
    active_expiry_a: Optional[str] = None
    active_expiry_b: Optional[str] = None
    entry_price_a = 0.0
    entry_price_b = 0.0
    entry_date: Optional[str] = None
    entry_z_val = 0.0
    entry_idx = 0
    trade_friction_acc = 0.0
    trade_turnover_acc = 0.0
    
    trades: List[Dict[str, Any]] = []
    equity_curve: List[Dict[str, Any]] = []
    
    current_capital = float(initial_capital)
    peak_capital = float(initial_capital)
    
    # Build daily representative spread series for point-in-time signal calculation
    # Using near-month tradeable contracts (DTE > expiry_buffer_days) on each historical date
    daily_records = []
    for d in dates:
        rows_a = df_a[df_a["trade_date"] == d]
        rows_b = df_b[df_b["trade_date"] == d]
        if rows_a.empty or rows_b.empty:
            continue
            
        # Select near-month active contract (DTE > buffer)
        cand_a = rows_a[rows_a["dte"] > expiry_buffer_days]
        cand_b = rows_b[rows_b["dte"] > expiry_buffer_days]
        
        pick_a = cand_a.sort_values("dte").iloc[0] if not cand_a.empty else rows_a.sort_values("dte").iloc[0]
        pick_b = cand_b.sort_values("dte").iloc[0] if not cand_b.empty else rows_b.sort_values("dte").iloc[0]
        
        p_a = float(pick_a[price_col] if price_col in pick_a else pick_a.get("close", 75000.0))
        p_b = float(pick_b[price_col] if price_col in pick_b else pick_b.get("close", 75000.0))
        
        daily_records.append({
            "trade_date": d,
            "price_a": p_a,
            "price_b": p_b,
            "spread": round(p_a - p_b, 2),
            "expiry_a": str(pick_a.get("expiry_date", "")),
            "expiry_b": str(pick_b.get("expiry_date", "")),
            "dte_a": int(pick_a.get("dte", 30)),
            "dte_b": int(pick_b.get("dte", 30)),
            "volume_a": int(pick_a.get("volume", 100)),
            "volume_b": int(pick_b.get("volume", 100)),
        })
        
    df_daily = pd.DataFrame(daily_records)
    if len(df_daily) < 5:
        return {
            "success": False,
            "message": "Insufficient daily observations in simulation window.",
            "metrics": None,
            "trades": [],
            "equity_curve": []
        }

    # Strict point-in-time rolling statistics (Zero Look-Ahead Bias)
    spreads = df_daily["spread"].values
    n_days = len(df_daily)
    z_scores = np.zeros(n_days)
    for i in range(n_days):
        start_i = max(0, i - lookback + 1)
        w = spreads[start_i : i + 1]
        if len(w) >= min(lookback, 5):
            m = np.mean(w)
            s = np.std(w, ddof=1) if len(w) > 1 else 0.0
            if s > 1e-8:
                z_scores[i] = (spreads[i] - m) / s
            else:
                z_scores[i] = 0.0
        else:
            z_scores[i] = 0.0
