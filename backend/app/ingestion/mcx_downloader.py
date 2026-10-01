"""
AurumIQ MCX Automated Downloader & Investigation Client
Investigates official MCX bhavcopy endpoints, verifies response schemas,
handles WAF/anti-bot status codes, and delegates to the CSV parser.
"""
from datetime import datetime
from typing import Dict, Any, Optional
import httpx
from app.ingestion.mcx_parser import (
    parse_requested_date,
    check_trading_day,
    parse_mcx_bhavcopy_file
)

OFFICIAL_MCX_BHAVCOPY_URL = "https://www.mcxindia.com/market-data/bhavcopy"

# Common historical / download endpoints investigated on MCX portal
INVESTIGATED_ENDPOINTS = [
    "https://www.mcxindia.com/market-data/bhavcopy",
    "https://www.mcxindia.com/Backpage.aspx/GetBhavCopyDateWise",
    "https://www.mcxindia.com/bhavcopy"
]

def attempt_mcx_direct_download(
    requested_date_str: str,
    timeout_sec: float = 8.0
) -> Dict[str, Any]:
    """
    Attempts to download Bhavcopy for requested_date (DD/MM/YYYY) from official MCX source.
    Investigates and validates server responses; does NOT assume schema or invent data.
    """
    # 1. Parse and validate requested date
    try:
        req_dt, req_iso = parse_requested_date(requested_date_str)
    except ValueError as e:
        return {
            "success": False,
            "status": "INVALID_DATE_FORMAT",
            "requested_date": requested_date_str,
            "message": str(e),
            "records": [],
            "source": "MCX_DIRECT_DOWNLOAD"
        }

    # 2. Check for weekend / closed exchange
    is_trading_day, day_reason = check_trading_day(req_dt)
    if not is_trading_day:
        return {
            "success": False,
            "status": "WEEKEND_HOLIDAY",
            "requested_date": req_iso,
            "actual_data_date": None,
            "message": day_reason,
            "records": [],
            "source": "MCX_DIRECT_DOWNLOAD"
        }

    # 3. Investigate official download endpoint
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": OFFICIAL_MCX_BHAVCOPY_URL
    }

    # Format date in MCX query styles: DD/MM/YYYY or YYYYMMDD
    formatted_date_ddmmyyyy = req_dt.strftime("%d/%m/%Y")
    
    try:
