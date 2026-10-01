"""
AurumIQ MCX Bhavcopy Parser & Ingestion Engine
Processes official MCX commodity bhavcopy formats with strict date validation,
compact expiry handling, symbol trimming, contract identification, and deduplication.
"""
import io
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from app.config import CONTRACT_SPECS

# Supported Bhavcopy column aliases for MCX
COLUMN_ALIASES = {
    "symbol": ["symbol", "commodity", "commodity_name", "instrument_name", "scrip"],
    "trade_date": ["date", "trade_date", "tradedate", "bhav_date", "report_date"],
    "expiry_date": ["expirydate", "expiry_date", "expiry", "exp_date", "contract_expiry"],
    "open": ["open", "open_price", "op"],
    "high": ["high", "high_price", "hp"],
    "low": ["low", "low_price", "lp"],
    "close": ["close", "close_price", "cp", "settlement_price", "settle_price"],
    "volume": ["volume", "traded_qty", "volume_lots", "total_volume", "contracts_traded", "volume(lots)"],
    "open_interest": ["openinterest", "open_interest", "oi", "open_int", "total_oi"]
}

def map_column_name(raw_name: str) -> str:
    cleaned = raw_name.strip().lower().replace(" ", "").replace("_", "").replace(".", "").replace("-", "")
    for target, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            norm_alias = alias.replace(" ", "").replace("_", "").replace(".", "").replace("-", "")
            if cleaned == norm_alias:
                return target
    return raw_name.strip().lower()

def parse_requested_date(requested_date_str: str) -> Tuple[datetime, str]:
    """
    Accepts requested date strictly in DD/MM/YYYY format (or ISO YYYY-MM-DD).
    Returns (datetime_obj, canonical_iso_str 'YYYY-MM-DD').
    """
    if not requested_date_str:
        raise ValueError("Requested date is required.")
        
    clean_str = requested_date_str.strip()
    
    # Try DD/MM/YYYY first (standard Indian exchange request format)
    for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]:
        try:
            dt = datetime.strptime(clean_str, fmt)
            return dt, dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
            
    raise ValueError(f"Invalid requested date format: '{requested_date_str}'. Expected DD/MM/YYYY (e.g. 04/10/2026).")

def check_trading_day(dt: datetime) -> Tuple[bool, str]:
    """
    Checks if requested date is a weekend (Saturday or Sunday).
    """
    weekday = dt.weekday()
    if weekday == 5:
        return False, f"{dt.strftime('%d/%m/%Y')} is a Saturday. MCX is closed on weekends."
    elif weekday == 6:
        return False, f"{dt.strftime('%d/%m/%Y')} is a Sunday. MCX is closed on weekends."
    return True, ""

def parse_compact_expiry_date(raw_expiry: Any) -> str:
    """
    Parses compact expiry dates such as 04SEP2026, 05NOV2024, 28FEB2025, 04-SEP-2026.
    Returns canonical ISO YYYY-MM-DD.
    """
    if not raw_expiry:
        raise ValueError("Expiry date is empty")
        
    s = str(raw_expiry).strip().upper()
    
    formats = [
        "%d%b%Y",    # 04SEP2026
        "%d-%b-%Y",  # 04-SEP-2026
        "%d/%m/%Y",  # 04/09/2026
        "%Y-%m-%d",  # 2026-09-04
        "%m/%d/%Y",  # 09/04/2026
        "%d%b%y",    # 04SEP26
        "%d-%b-%y",  # 04-SEP-26
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
            
    raise ValueError(f"Unable to parse compact expiry date: '{raw_expiry}'")

def parse_trading_date(raw_date: Any, target_dt: Optional[datetime] = None) -> str:
    """
    Parses trading date from Bhavcopy file.
    Validates actual returned trading date which may be expressed as MM/DD/YYYY or DD/MM/YYYY.
    """
    if not raw_date:
        raise ValueError("Trade date is empty")
        
    s = str(raw_date).strip().upper()
    
    # If target_dt is provided, check if either MM/DD/YYYY or DD/MM/YYYY aligns with target_dt
    if target_dt:
        target_iso = target_dt.strftime("%Y-%m-%d")
        # Try MM/DD/YYYY and DD/MM/YYYY specifically against target
        for fmt in ["%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%b-%Y", "%d-%m-%Y"]:
            try:
                dt = datetime.strptime(s, fmt)
                if dt.strftime("%Y-%m-%d") == target_iso:
                    return target_iso
            except ValueError:
                continue

    # Fallback to standard parsing order (MM/DD/YYYY is common in MCX Bhavcopy exports)
    formats = [
        "%m/%d/%Y",  # MCX often exports in US MM/DD/YYYY format
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%d-%b-%Y",
        "%d-%m-%Y",
        "%d%b%Y"
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
            
    raise ValueError(f"Unable to parse trade date: '{raw_date}'")

def clean_numeric(val: Any, field_name: str, allow_zero: bool = False) -> float:
    """Cleans numeric values by removing commas, whitespace, and validating bounds."""
    if val is None:
        raise ValueError(f"Missing {field_name}")
    s = str(val).strip().replace(",", "")
    if s in ["", "-", "N.A.", "NA", "NULL", "nan"]:
        raise ValueError(f"Non-numeric value in {field_name}: '{val}'")
    try:
        num = float(s)
    except ValueError:
        raise ValueError(f"Invalid float in {field_name}: '{val}'")
        
    if not allow_zero and num <= 0:
        raise ValueError(f"{field_name} must be strictly positive (got {num})")
    if allow_zero and num < 0:
        raise ValueError(f"{field_name} cannot be negative (got {num})")
        
    return num

def parse_mcx_bhavcopy_file(
    content: str,
    requested_date_str: Optional[str] = None,
    source: str = "CSV_UPLOAD"
) -> Dict[str, Any]:
    """
    Parses and validates downloaded or uploaded MCX Bhavcopy files.
    - Strips padding from symbols
    - Identifies contract using (symbol, expiry_date)
    - Validates actual data date against requested date (DD/MM/YYYY)
    - Rejects date mismatches without silently treating old data as requested date
    - Deduplicates records
    """
    # 1. Parse requested date if provided
    req_dt = None
    req_iso = None
    if requested_date_str:
        try:
            req_dt, req_iso = parse_requested_date(requested_date_str)
            # Check weekend
            is_valid_day, reason = check_trading_day(req_dt)
            if not is_valid_day:
                return {
                    "success": False,
                    "status": "WEEKEND_HOLIDAY",
                    "source": source,
                    "requested_date": req_iso,
                    "actual_data_date": None,
                    "message": reason,
                    "records": [],
                    "raw_records": [],
                    "validation_report": {
                        "total_extracted": 0,
                        "valid_count": 0,
                        "rejected_count": 0,
                        "duplicate_count": 0,
                        "rejected_samples": [{"reason": reason}]
                    }
                }
        except ValueError as e:
            return {
                "success": False,
                "status": "INVALID_REQUESTED_DATE",
                "source": source,
                "requested_date": requested_date_str,
                "actual_data_date": None,
                "message": str(e),
                "records": [],
                "raw_records": [],
                "validation_report": None
            }

    # 2. Parse CSV text
    if not content or not content.strip():
        return {
            "success": False,
            "status": "EMPTY_FILE",
            "source": source,
            "requested_date": req_iso,
            "actual_data_date": None,
            "message": "Supplied Bhavcopy content is empty.",
            "records": [],
            "raw_records": [],
            "validation_report": None
        }

    try:
        df = pd.read_csv(io.StringIO(content))
    except Exception as e:
        return {
            "success": False,
            "status": "MALFORMED_FILE",
            "source": source,
            "requested_date": req_iso,
            "actual_data_date": None,
            "message": f"Malformed CSV structure: {str(e)}",
            "records": [],
            "raw_records": [],
            "validation_report": None
        }

    # 3. Column name mapping
    col_mapping = {col: map_column_name(col) for col in df.columns}
    df = df.rename(columns=col_mapping)

    required_cols = ["symbol", "trade_date", "expiry_date", "open", "high", "low", "close"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        return {
            "success": False,
            "status": "MISSING_COLUMNS",
            "source": source,
            "requested_date": req_iso,
            "actual_data_date": None,
            "message": f"Missing required Bhavcopy columns: {missing}. Available: {list(df.columns)}",
            "records": [],
            "raw_records": [],
            "validation_report": None
        }

    if "volume" not in df.columns:
        df["volume"] = 0
    if "open_interest" not in df.columns:
        df["open_interest"] = 0

    # 4. Filter for our target gold contracts with stripped symbol padding
    allowed_symbols = {"GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"}
    
    # Raw symbol stripping
    df["raw_symbol"] = df["symbol"].astype(str)
    df["clean_symbol"] = df["raw_symbol"].str.strip().str.upper()
    df_gold = df[df["clean_symbol"].isin(allowed_symbols)].copy()

    if df_gold.empty:
        return {
            "success": False,
            "status": "NO_GOLD_CONTRACTS",
            "source": source,
            "requested_date": req_iso,
            "actual_data_date": None,
            "message": "No MCX Gold contracts (GOLDM, GOLDTEN, GOLDGUINEA, GOLDPETAL) found in file.",
            "records": [],
            "raw_records": [],
            "validation_report": {
                "total_extracted": len(df),
                "valid_count": 0,
                "rejected_count": len(df),
                "duplicate_count": 0,
                "rejected_samples": [{"reason": "Non-gold commodity contracts skipped"}]
            }
        }

    # 5. Process and validate rows
    valid_market_records = []
    raw_audit_records = []
    rejections = []
    seen_contract_keys = set()
    duplicate_count = 0
    detected_trade_dates = set()

    for idx, row in df_gold.iterrows():
        raw_sym = str(row["raw_symbol"])
        clean_sym = str(row["clean_symbol"])
        raw_t_date = str(row["trade_date"])
        raw_exp_date = str(row["expiry_date"])
        
        row_json = {
            "symbol": raw_sym,
            "trade_date": raw_t_date,
            "expiry_date": raw_exp_date,
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "volume": row["volume"],
            "open_interest": row["open_interest"]
        }

        # Validate dates
        try:
            clean_t_date = parse_trading_date(raw_t_date, target_dt=req_dt)
            detected_trade_dates.add(clean_t_date)
        except ValueError as e:
            rejections.append({"row_index": idx, "reason": str(e), "raw": row_json})
            raw_audit_records.append({
                "raw_symbol": raw_sym, "clean_symbol": clean_sym,
                "raw_trade_date": raw_t_date, "clean_trade_date": None,
                "raw_expiry_date": raw_exp_date, "clean_expiry_date": None,
                "contract_id": None, "open": None, "high": None, "low": None, "close": None,
                "volume": 0, "open_interest": 0, "is_valid": 0, "validation_error": str(e)
            })
            continue

        try:
            clean_exp_date = parse_compact_expiry_date(raw_exp_date)
        except ValueError as e:
            rejections.append({"row_index": idx, "reason": str(e), "raw": row_json})
            raw_audit_records.append({
                "raw_symbol": raw_sym, "clean_symbol": clean_sym,
                "raw_trade_date": raw_t_date, "clean_trade_date": clean_t_date,
                "raw_expiry_date": raw_exp_date, "clean_expiry_date": None,
                "contract_id": None, "open": None, "high": None, "low": None, "close": None,
                "volume": 0, "open_interest": 0, "is_valid": 0, "validation_error": str(e)
            })
            continue

        # Expiry must be >= trade date
        if clean_exp_date < clean_t_date:
            err = f"Expiry date {clean_exp_date} is before trade date {clean_t_date}"
            rejections.append({"row_index": idx, "reason": err, "raw": row_json})
            raw_audit_records.append({
                "raw_symbol": raw_sym, "clean_symbol": clean_sym,
                "raw_trade_date": raw_t_date, "clean_trade_date": clean_t_date,
                "raw_expiry_date": raw_exp_date, "clean_expiry_date": clean_exp_date,
                "contract_id": f"{clean_sym}_{clean_exp_date}",
                "open": None, "high": None, "low": None, "close": None,
                "volume": 0, "open_interest": 0, "is_valid": 0, "validation_error": err
            })
            continue

        # Composite contract identifier: SYMBOL + EXPIRY
        contract_key = (clean_sym, clean_exp_date, clean_t_date)
        if contract_key in seen_contract_keys:
            duplicate_count += 1
            rejections.append({
                "row_index": idx,
                "reason": f"Duplicate record for contract {clean_sym} expiry {clean_exp_date} on {clean_t_date}",
                "raw": row_json
            })
            continue
        seen_contract_keys.add(contract_key)

        # Validate numeric fields
        try:
            open_p = clean_numeric(row["open"], "Open Price")
            high_p = clean_numeric(row["high"], "High Price")
            low_p = clean_numeric(row["low"], "Low Price")
            close_p = clean_numeric(row["close"], "Close Price")
            vol = int(clean_numeric(row["volume"], "Volume", allow_zero=True))
            oi = int(clean_numeric(row["open_interest"], "Open Interest", allow_zero=True))
        except ValueError as e:
            rejections.append({"row_index": idx, "reason": str(e), "raw": row_json})
            raw_audit_records.append({
                "raw_symbol": raw_sym, "clean_symbol": clean_sym,
                "raw_trade_date": raw_t_date, "clean_trade_date": clean_t_date,
                "raw_expiry_date": raw_exp_date, "clean_expiry_date": clean_exp_date,
                "contract_id": f"{clean_sym}_{clean_exp_date}",
                "open": None, "high": None, "low": None, "close": None,
                "volume": 0, "open_interest": 0, "is_valid": 0, "validation_error": str(e)
            })
            continue

        # OHLC Sanity Check
        eps = 0.01
        if high_p + eps < low_p:
            err = f"High ({high_p}) is lower than Low ({low_p})"
            rejections.append({"row_index": idx, "reason": err, "raw": row_json})
            continue
        if high_p + eps < open_p or high_p + eps < close_p:
            err = f"High ({high_p}) is lower than Open ({open_p}) or Close ({close_p})"
            rejections.append({"row_index": idx, "reason": err, "raw": row_json})
            continue
        if low_p - eps > open_p or low_p - eps > close_p:
            err = f"Low ({low_p}) is higher than Open ({open_p}) or Close ({close_p})"
            rejections.append({"row_index": idx, "reason": err, "raw": row_json})
            continue

        # Normalization and Contract Spec checks
        spec = CONTRACT_SPECS[clean_sym]
        norm_10g = close_p * spec.multiplier_to_10g
        purity_adj_10g = norm_10g * (999.0 / spec.purity)
        
        t_dt_obj = datetime.strptime(clean_t_date, "%Y-%m-%d")
        exp_dt_obj = datetime.strptime(clean_exp_date, "%Y-%m-%d")
        dte = max(1, (exp_dt_obj - t_dt_obj).days)

        # Sanity price bounds for MCX Gold per 10g (₹30,000 to ₹180,000)
        if norm_10g < 30000 or norm_10g > 180000:
            err = f"Normalized price ₹{norm_10g:.2f}/10g outside plausible MCX bounds (₹30k - ₹180k)"
            rejections.append({"row_index": idx, "reason": err, "raw": row_json})
            continue

        contract_id = f"{clean_sym}_{clean_exp_date}"
        
        valid_market_records.append({
            "symbol": clean_sym,
            "trade_date": clean_t_date,
            "expiry_date": clean_exp_date,
            "contract_id": contract_id,
            "open": round(open_p, 2),
            "high": round(high_p, 2),
