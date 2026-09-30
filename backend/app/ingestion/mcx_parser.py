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
