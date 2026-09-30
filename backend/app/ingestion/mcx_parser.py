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
