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
        with httpx.Client(timeout=timeout_sec, follow_redirects=True, headers=headers) as client:
            resp = client.get(OFFICIAL_MCX_BHAVCOPY_URL)
            
            # Check response status
            if resp.status_code == 403:
                return {
                    "success": False,
                    "status": "FETCH_BLOCKED",
                    "http_status": 403,
                    "requested_date": req_iso,
                    "actual_data_date": None,
                    "message": (
                        "MCX India portal blocked direct programmatic download (HTTP 403 Forbidden / Akamai WAF). "
                        "The exchange requires manual user browser interaction on https://www.mcxindia.com/market-data/bhavcopy. "
                        "Please use the CSV upload fallback below to import the downloaded file."
                    ),
                    "source": "MCX_DIRECT_DOWNLOAD",
                    "official_url": OFFICIAL_MCX_BHAVCOPY_URL,
                    "records": []
                }
            elif resp.status_code != 200:
                return {
                    "success": False,
                    "status": f"HTTP_ERROR_{resp.status_code}",
                    "http_status": resp.status_code,
                    "requested_date": req_iso,
                    "actual_data_date": None,
                    "message": f"MCX server responded with HTTP {resp.status_code}.",
                    "source": "MCX_DIRECT_DOWNLOAD",
                    "official_url": OFFICIAL_MCX_BHAVCOPY_URL,
                    "records": []
                }
                
            # If 200 returned, check if body is CSV or HTML portal
            content_type = resp.headers.get("content-type", "").lower()
            text_preview = resp.text[:200].lower()
            
            if "csv" in content_type or "symbol" in text_preview or "commodity" in text_preview:
                # Direct CSV returned! Pass to parser
                return parse_mcx_bhavcopy_file(
                    content=resp.text,
                    requested_date_str=requested_date_str,
                    source="MCX_DIRECT_DOWNLOAD"
                )
            else:
                # HTML page returned (form requiring ASPX viewstate / date submission)
                return {
                    "success": False,
                    "status": "DYNAMIC_PORTAL_INTERACTION_REQUIRED",
                    "requested_date": req_iso,
                    "actual_data_date": None,
                    "message": (
                        "MCX Bhavcopy portal serves an ASP.NET dynamic page requiring session tokens and client-side JavaScript execution. "
                        "As per institutional data governance without unauthorized scraping, please download the daily CSV from "
                        "https://www.mcxindia.com/market-data/bhavcopy and upload it using the reliable CSV Upload fallback below."
                    ),
                    "source": "MCX_DIRECT_DOWNLOAD",
                    "official_url": OFFICIAL_MCX_BHAVCOPY_URL,
                    "records": []
                }
                
    except httpx.RequestError as e:
        return {
            "success": False,
            "status": "NETWORK_ERROR",
            "requested_date": req_iso,
            "actual_data_date": None,
            "message": f"Network connection to MCX failed: {str(e)}",
            "source": "MCX_DIRECT_DOWNLOAD",
            "official_url": OFFICIAL_MCX_BHAVCOPY_URL,
            "records": []
        }
