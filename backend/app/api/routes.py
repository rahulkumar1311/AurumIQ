"""
AurumIQ API Routes Implementation
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Response
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import pandas as pd
from app.database.connection import get_db
from app.config import CONTRACT_SPECS
from app.signal.spread_engine import calculate_spread_series
from app.backtesting.engine import run_spread_backtest
from app.ingestion.sample_data_loader import load_sample_data_into_db
from app.ingestion.mcx_parser import parse_bhavcopy_csv, parse_mcx_bhavcopy_file
from app.ingestion.mcx_downloader import attempt_mcx_direct_download
from app.ingestion.storage import save_bhavcopy_import_audit, get_recent_bhavcopy_imports
from app.normalization.normalizer import default_engine

router = APIRouter()

# ----------------- Health Check -----------------
@router.get("/health")
def get_health() -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM market_data;")
        total_records = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(DISTINCT symbol) as sym_count FROM market_data;")
        active_symbols = cursor.fetchone()["sym_count"]
        
        cursor.execute("SELECT COUNT(DISTINCT trade_date) as day_count FROM market_data;")
        total_days = cursor.fetchone()["day_count"]
        
        cursor.execute("SELECT MAX(trade_date) as max_date, MIN(trade_date) as min_date FROM market_data;")
        date_row = cursor.fetchone()
        
    return {
        "status": "healthy",
        "service": "AurumIQ Commodity Derivatives Intelligence",
        "database": "sqlite_connected",
        "total_market_records": total_records,
        "total_trading_days": total_days,
        "active_symbols": active_symbols,
        "date_range": {
            "start": date_row["min_date"] if total_records > 0 else None,
            "end": date_row["max_date"] if total_records > 0 else None
        },
        "has_data": total_records > 0
    }

# ----------------- Normalization Engine Endpoints -----------------
@router.get("/normalization/assumptions")
def get_normalization_assumptions() -> Dict[str, Any]:
    """Returns complete normalization assumptions, mathematical formulas, and contract factors."""
    return default_engine.get_assumptions_report()

@router.get("/normalization/report")
def download_normalization_report(format: str = "csv") -> Response:
    """Generates downloadable normalization audit report in CSV format."""
    assumptions = default_engine.get_assumptions_report()
    factors = assumptions["contract_factors"]
    
    df = pd.DataFrame(factors)
    # Add formulas, audit references and notes
    df["reference_basis"] = assumptions["reference_standard"]["description"]
    df["audit_source"] = assumptions["audit_metadata"]["official_source_url"]
    df["audit_date"] = assumptions["audit_metadata"]["audit_date"]
    df["flagged_assumption_summary"] = assumptions["purity_convention"]["flagged_assumption"]
    
    csv_data = df.to_csv(index=False)
    headers = {
        "Content-Disposition": "attachment; filename=aurumiq_normalization_audit_report.csv",
        "Content-Type": "text/csv; charset=utf-8"
    }
    return Response(content=csv_data, media_type="text/csv", headers=headers)

# ----------------- Overview Dashboard -----------------
@router.get("/overview")
def get_overview() -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM market_data;")
        cnt = cursor.fetchone()["cnt"]
        assumptions = default_engine.get_assumptions_report()
        
        if cnt == 0:
            # Return empty state structure with specs
            specs_list = [spec.model_dump() for spec in CONTRACT_SPECS.values()]
            return {
                "has_data": False,
                "message": "No market data available in local database. Ingest MCX Bhavcopy or load sample dataset to view analytics.",
                "contracts": specs_list,
                "quotes": [],
                "spread_matrix": [],
                "normalization_assumptions": assumptions
            }
            
        # Get latest available trade date
        cursor.execute("SELECT MAX(trade_date) as latest_date FROM market_data;")
        latest_date = cursor.fetchone()["latest_date"]
        
        # Get near-month contracts for latest date (minimum DTE for each contract)
        cursor.execute("""
            SELECT m.*
            FROM market_data m
            INNER JOIN (
                SELECT symbol, MIN(dte) as min_dte
                FROM market_data
                WHERE trade_date = ?
                GROUP BY symbol
            ) sub ON m.symbol = sub.symbol AND m.dte = sub.min_dte
            WHERE m.trade_date = ?
            ORDER BY m.symbol;
        """, (latest_date, latest_date))
        
        rows = [dict(r) for r in cursor.fetchall()]
        
        # Build pairwise spread matrix on normalized 10g close
        symbols = [r["symbol"] for r in rows]
        price_map = {r["symbol"]: r["normalized_close_10g"] for r in rows}
        matrix = []
        for s1 in symbols:
            row_dict = {"symbol": s1}
            for s2 in symbols:
                if s1 in price_map and s2 in price_map:
                    row_dict[s2] = round(price_map[s1] - price_map[s2], 2)
                else:
                    row_dict[s2] = None
            matrix.append(row_dict)
            
        specs_list = [CONTRACT_SPECS[r["symbol"]].model_dump() for r in rows]
        
        return {
            "has_data": True,
            "latest_trade_date": latest_date,
            "contracts": specs_list,
            "quotes": rows,
            "spread_matrix": matrix,
            "normalization_assumptions": assumptions
        }

# ----------------- Cross-Contract Comparison -----------------
@router.get("/cross-contract")
def get_cross_contract(expiry_filter: Optional[str] = None) -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM market_data;")
        if cursor.fetchone()["cnt"] == 0:
            return {
                "has_data": False,
                "message": "No market data available.",
                "history": [],
                "basis_curve": [],
                "liquidity": []
            }
            
        # Get near-month series for each contract across dates
        cursor.execute("""
            SELECT m.trade_date, m.symbol, m.close, m.normalized_close_10g,
                   m.purity_adjusted_10g, m.volume, m.open_interest, m.dte, m.implied_basis_pct
            FROM market_data m
            INNER JOIN (
                SELECT trade_date, symbol, MIN(dte) as min_dte
                FROM market_data
                GROUP BY trade_date, symbol
            ) sub ON m.trade_date = sub.trade_date AND m.symbol = sub.symbol AND m.dte = sub.min_dte
            ORDER BY m.trade_date ASC;
        """)
        records = [dict(r) for r in cursor.fetchall()]
        
    df = pd.DataFrame(records)
    if df.empty:
        return {"has_data": False, "history": [], "basis_curve": [], "liquidity": []}
        
    # Pivot normalized prices by date
    pivot_norm = df.pivot(index="trade_date", columns="symbol", values="normalized_close_10g").reset_index()
    history = pivot_norm.to_dict(orient="records")

    # Pivot purity-adjusted prices by date
    pivot_purity = df.pivot(index="trade_date", columns="symbol", values="purity_adjusted_10g").reset_index()
    history_purity = pivot_purity.to_dict(orient="records")
    
    # Latest basis & carry curve across contracts and expiries
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(trade_date) as max_date FROM market_data;")
        max_date = cursor.fetchone()["max_date"]
        
        cursor.execute("""
            SELECT symbol, expiry_date, dte, normalized_close_10g, implied_basis_pct, volume, open_interest
            FROM market_data
            WHERE trade_date = ?
            ORDER BY symbol, dte ASC;
        """, (max_date,))
