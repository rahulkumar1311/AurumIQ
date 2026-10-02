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
        basis_curve = [dict(r) for r in cursor.fetchall()]
        
        # Liquidity aggregates
        cursor.execute("""
            SELECT symbol, SUM(volume) as total_volume, AVG(open_interest) as avg_oi,
                   AVG(volume) as avg_daily_volume
            FROM market_data
            GROUP BY symbol;
        """)
        liquidity = [dict(r) for r in cursor.fetchall()]
        
    return {
        "has_data": True,
        "latest_date": max_date,
        "history": history,
        "history_purity_adjusted": history_purity,
        "basis_curve": basis_curve,
        "liquidity": liquidity
    }

# ----------------- Expiry Dates Query -----------------
@router.get("/expiries")
def get_available_expiries() -> Dict[str, Any]:
    """Returns available trading expiries for each contract in local database."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT symbol, expiry_date FROM market_data ORDER BY symbol, expiry_date ASC;")
        rows = cursor.fetchall()
        result: Dict[str, List[str]] = {}
        for r in rows:
            sym = r["symbol"]
            exp = r["expiry_date"]
            if sym not in result:
                result[sym] = []
            result[sym].append(exp)
        return {"expiries": result}

# ----------------- Historical Spread & Relative-Value Analysis -----------------
@router.get("/spreads")
def get_spreads(
    pair_a: str = "GOLDM",
    expiry_a: Optional[str] = None,
    pair_b: str = "GOLDPETAL",
    expiry_b: Optional[str] = None,
    lookback: int = 20,
    purity_adjusted: bool = False,
    z_threshold: float = 2.0,
    exit_threshold: float = 0.5,
    min_observations: int = 10,
    friction_per_10g: Optional[float] = None
) -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM market_data;")
        if cursor.fetchone()["cnt"] == 0:
            return {
                "has_data": False,
                "message": "No market data available.",
                "series": [],
                "statistics": None,
                "signal": {
                    "signal_type": "NO_SIGNAL",
                    "signal_label": "No actionable signal",
                    "is_actionable": False,
                    "reasons": ["Database empty. Please load or ingest MCX data."]
                },
                "data_quality_warnings": ["Database contains 0 records."]
            }
            
        # Extract series for pair_a (specific expiry or near-month minimum DTE)
        if expiry_a and expiry_a.strip() and expiry_a.strip().lower() not in ("all", "near-month", "none", ""):
            query_a = "SELECT * FROM market_data WHERE symbol = ? AND expiry_date = ? ORDER BY trade_date ASC;"
            cursor.execute(query_a, (pair_a, expiry_a.strip()))
        else:
            query_a = """
                SELECT m.*
                FROM market_data m
                INNER JOIN (
                    SELECT trade_date, symbol, MIN(dte) as min_dte
                    FROM market_data
                    WHERE symbol = ?
                    GROUP BY trade_date, symbol
                ) sub ON m.trade_date = sub.trade_date AND m.symbol = sub.symbol AND m.dte = sub.min_dte
                ORDER BY m.trade_date ASC;
            """
            cursor.execute(query_a, (pair_a,))
        rows_a = [dict(r) for r in cursor.fetchall()]
        
        # Extract series for pair_b (specific expiry or near-month minimum DTE)
        if expiry_b and expiry_b.strip() and expiry_b.strip().lower() not in ("all", "near-month", "none", ""):
            query_b = "SELECT * FROM market_data WHERE symbol = ? AND expiry_date = ? ORDER BY trade_date ASC;"
            cursor.execute(query_b, (pair_b, expiry_b.strip()))
        else:
            query_b = """
                SELECT m.*
                FROM market_data m
                INNER JOIN (
                    SELECT trade_date, symbol, MIN(dte) as min_dte
                    FROM market_data
                    WHERE symbol = ?
                    GROUP BY trade_date, symbol
                ) sub ON m.trade_date = sub.trade_date AND m.symbol = sub.symbol AND m.dte = sub.min_dte
                ORDER BY m.trade_date ASC;
            """
            cursor.execute(query_b, (pair_b,))
        rows_b = [dict(r) for r in cursor.fetchall()]
        
    df_a = pd.DataFrame(rows_a)
    df_b = pd.DataFrame(rows_b)
    
    result = calculate_spread_series(
        df_a=df_a,
        df_b=df_b,
        symbol_a=pair_a,
        symbol_b=pair_b,
        lookback=lookback,
        use_purity_adjusted=purity_adjusted,
        z_threshold=z_threshold,
        exit_threshold=exit_threshold,
        min_observations=min_observations,
        friction_per_10g=friction_per_10g
    )
    
    return {
        "has_data": len(result.get("series", [])) > 0,
        **result
    }

# ----------------- Backtesting Lab -----------------
class BacktestRequest(BaseModel):
    pair_a: str = "GOLDM"
    pair_b: str = "GOLDPETAL"
    entry_z: float = 1.5
    exit_z: float = 0.2
    stop_loss_z: float = 3.0
    lookback: int = 20
    initial_capital: float = 500000.0
    use_purity_adjusted: bool = False
    include_friction: bool = True
    dev_ratio: float = 0.50
    val_ratio: float = 0.25
    test_ratio: float = 0.25
    expiry_buffer_days: int = 3
    auto_calibrate: bool = False

@router.post("/backtest/run")
def execute_backtest(req: BacktestRequest) -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM market_data;")
        if cursor.fetchone()["cnt"] == 0:
            return {
                "has_data": False,
                "success": False,
                "message": "No market data loaded. Ingest data to perform backtest.",
                "metrics": None,
                "walk_forward_splits": None,
                "trades": [],
                "equity_curve": []
            }
            
        cursor.execute("SELECT * FROM market_data WHERE symbol = ? ORDER BY trade_date ASC, dte ASC;", (req.pair_a,))
        df_a = pd.DataFrame([dict(r) for r in cursor.fetchall()])
        
        cursor.execute("SELECT * FROM market_data WHERE symbol = ? ORDER BY trade_date ASC, dte ASC;", (req.pair_b,))
        df_b = pd.DataFrame([dict(r) for r in cursor.fetchall()])

        cursor.execute("""
            SELECT trade_date, normalized_close_10g, close
            FROM market_data
            WHERE symbol = 'GOLDM'
            GROUP BY trade_date
            ORDER BY trade_date ASC;
        """)
        df_bench = pd.DataFrame([dict(r) for r in cursor.fetchall()])
        
    res = run_spread_backtest(
        df_a=df_a,
        df_b=df_b,
        pair_a=req.pair_a,
        pair_b=req.pair_b,
        entry_z=req.entry_z,
        exit_z=req.exit_z,
        stop_loss_z=req.stop_loss_z,
        lookback=req.lookback,
        initial_capital=req.initial_capital,
        use_purity_adjusted=req.use_purity_adjusted,
        include_friction=req.include_friction,
        dev_ratio=req.dev_ratio,
        val_ratio=req.val_ratio,
        test_ratio=req.test_ratio,
        expiry_buffer_days=req.expiry_buffer_days,
        auto_calibrate=req.auto_calibrate,
        benchmark_df=df_bench
    )
    
    return {
        "has_data": True,
        **res
    }

@router.post("/backtest/report")
def download_backtest_report(req: BacktestRequest) -> Response:
    """Generates downloadable institutional walk-forward backtest audit report in CSV format."""
    from app.backtesting.engine import generate_backtest_report_csv
    res = execute_backtest(req)
    csv_text = generate_backtest_report_csv(res)
    headers = {
        "Content-Disposition": f"attachment; filename=aurumiq_walk_forward_backtest_{req.pair_a}_{req.pair_b}.csv",
        "Content-Type": "text/csv; charset=utf-8"
    }
    return Response(content=csv_text, media_type="text/csv", headers=headers)

# ----------------- Data Quality & Contract Calendar -----------------
@router.get("/data-quality")
def get_data_quality() -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM market_data;")
        cnt = cursor.fetchone()["cnt"]
        
        if cnt == 0:
            return {
                "has_data": False,
                "total_records": 0,
                "date_range": None,
                "calendar": [],
                "anomalies": [],
                "ingestion_logs": []
            }
            
        cursor.execute("SELECT MIN(trade_date) as start_date, MAX(trade_date) as end_date FROM market_data;")
        date_range = dict(cursor.fetchone())
        
        # Expiry calendar
        cursor.execute("""
            SELECT DISTINCT symbol, expiry_date,
                   ROUND(AVG(normalized_close_10g), 2) as avg_norm_price,
                   SUM(volume) as total_volume,
                   MAX(open_interest) as max_oi,
                   MIN(dte) as current_dte
            FROM market_data
            GROUP BY symbol, expiry_date
            ORDER BY expiry_date ASC, symbol;
        """)
        calendar = [dict(r) for r in cursor.fetchall()]
        
        # Audit logs
        cursor.execute("SELECT * FROM ingestion_logs ORDER BY timestamp DESC LIMIT 10;")
        logs = [dict(r) for r in cursor.fetchall()]
        
        # Price anomaly check (spread deviation > 3% between identical purity contracts)
        cursor.execute("""
            SELECT trade_date, symbol, normalized_close_10g, volume
            FROM market_data
            WHERE normalized_close_10g < 35000 OR normalized_close_10g > 150000;
        """)
        anomalies = [dict(r) for r in cursor.fetchall()]
        
    bhavcopy_imports = get_recent_bhavcopy_imports(limit=15)
        
    return {
        "has_data": True,
        "total_records": cnt,
        "date_range": date_range,
        "calendar": calendar,
        "anomalies": anomalies,
        "ingestion_logs": logs,
        "bhavcopy_imports": bhavcopy_imports
    }

class BhavcopyDownloadRequest(BaseModel):
    requested_date: str  # DD/MM/YYYY

@router.post("/bhavcopy/download")
def download_mcx_bhavcopy(req: BhavcopyDownloadRequest) -> Dict[str, Any]:
    """
    Attempts to download and ingest MCX Bhavcopy for requested_date (DD/MM/YYYY).
    Persists raw records, audit logs, and validation diagnostics.
    """
    download_res = attempt_mcx_direct_download(req.requested_date)
    import_id = save_bhavcopy_import_audit(download_res, source="MCX_DIRECT_DOWNLOAD")
    download_res["import_id"] = import_id
    return download_res

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB

def _validate_uploaded_file(file: UploadFile, content: bytes) -> None:
    if file.filename:
        filename_lower = file.filename.lower()
        if not (filename_lower.endswith(".csv") or filename_lower.endswith(".txt")):
            raise HTTPException(
                status_code=400,
                detail="Invalid file format. Only MCX Bhavcopy CSV (.csv) or text (.txt) files are accepted."
            )
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File size exceeds maximum permitted limit of 25MB."
        )

@router.post("/bhavcopy/upload")
async def upload_mcx_bhavcopy(
    file: UploadFile = File(...),
    requested_date: Optional[str] = Form(None)
) -> Dict[str, Any]:
    """
    Imports uploaded MCX Bhavcopy CSV file with date validation against requested_date.
    Strips symbol padding, parses compact expiries, detects duplicates and date mismatches.
    """
    content = await file.read()
    _validate_uploaded_file(file, content)
    csv_text = content.decode("utf-8", errors="ignore")
    parse_res = parse_mcx_bhavcopy_file(
        content=csv_text,
        requested_date_str=requested_date,
        source=f"CSV_UPLOAD ({file.filename})"
    )
    import_id = save_bhavcopy_import_audit(parse_res, source=f"CSV_UPLOAD ({file.filename})")
    parse_res["import_id"] = import_id
    return parse_res

@router.get("/bhavcopy/imports")
def get_bhavcopy_import_history() -> Dict[str, Any]:
    """Returns recent bhavcopy ingestion audit history."""
    imports = get_recent_bhavcopy_imports(limit=25)
    return {
        "count": len(imports),
        "imports": imports
    }

@router.post("/data-quality/ingest-sample")
def ingest_sample() -> Dict[str, Any]:
    res = load_sample_data_into_db()
    return res

@router.post("/data-quality/reset")
def reset_database() -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM market_data;")
        cursor.execute("DELETE FROM backtest_runs;")
        cursor.execute("DELETE FROM ingestion_logs;")
        cursor.execute("DELETE FROM raw_bhavcopy_records;")
        cursor.execute("DELETE FROM validation_logs;")
        cursor.execute("DELETE FROM raw_bhavcopy_imports;")
    return {"status": "success", "message": "Database reset to initial empty state."}

@router.post("/data-quality/upload-csv")
