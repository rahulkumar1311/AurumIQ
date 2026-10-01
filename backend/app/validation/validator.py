"""
AurumIQ Data Validation Module
Ensures high institutional data integrity, checks contract specs, detects outliers, and validates OHLC integrity.
"""
from datetime import datetime
from typing import Dict, Any, List, Tuple
from app.config import CONTRACT_SPECS

class ValidationError(Exception):
    pass

def parse_date(date_str: Any) -> str:
    """Parse date strings in standard formats to YYYY-MM-DD."""
    if not date_str:
        raise ValueError("Empty date string")
    
    clean_str = str(date_str).strip()
    # Try common exchange formats
    formats = [
        "%Y-%m-%d",
        "%d-%b-%Y",  # 05-NOV-2024
        "%d-%m-%Y",  # 05-11-2024
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d%b%Y",    # 05NOV2024
    ]
    for fmt in formats:
        try:
            return datetime.strptime(clean_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {date_str}")

def validate_market_record(record: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validates a single market bar record.
    Returns (is_valid, error_reason, cleaned_record).
    """
    symbol = str(record.get("symbol", "")).strip().upper()
    if symbol not in CONTRACT_SPECS:
        return False, f"Unsupported commodity symbol: {symbol}. Must be one of {list(CONTRACT_SPECS.keys())}", {}

    try:
        trade_date = parse_date(record.get("trade_date"))
        expiry_date = parse_date(record.get("expiry_date"))
    except ValueError as e:
        return False, f"Invalid date: {str(e)}", {}

    if expiry_date < trade_date:
        return False, f"Expiry date {expiry_date} is before trade date {trade_date}", {}

    try:
        open_p = float(record.get("open", 0.0))
        high_p = float(record.get("high", 0.0))
        low_p = float(record.get("low", 0.0))
        close_p = float(record.get("close", 0.0))
        volume = int(record.get("volume", 0))
        oi = int(record.get("open_interest", 0))
    except (ValueError, TypeError) as e:
        return False, f"Non-numeric market values: {str(e)}", {}

    if close_p <= 0 or open_p <= 0 or high_p <= 0 or low_p <= 0:
        return False, "Price values must be strictly positive", {}

    # Allow slight floating point tolerance for OHLC consistency
    eps = 0.01
    if high_p + eps < low_p:
        return False, f"High price ({high_p}) is lower than Low price ({low_p})", {}

    if high_p + eps < open_p or high_p + eps < close_p:
        return False, f"High ({high_p}) is lower than Open ({open_p}) or Close ({close_p})", {}

    if low_p - eps > open_p or low_p - eps > close_p:
        return False, f"Low ({low_p}) is higher than Open ({open_p}) or Close ({close_p})", {}

    if volume < 0 or oi < 0:
        return False, f"Volume ({volume}) or Open Interest ({oi}) cannot be negative", {}

