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
