import os
from pathlib import Path
from pydantic import BaseModel
from typing import Dict

BASE_DIR = Path(__file__).resolve().parent.parent
custom_data_dir = os.getenv("AURUMIQ_DATA_DIR")
DATA_DIR = Path(custom_data_dir).resolve() if custom_data_dir else BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

custom_db_path = os.getenv("AURUMIQ_DB_PATH")
DB_PATH = Path(custom_db_path).resolve() if custom_db_path else DATA_DIR / "aurumiq.db"

class ContractSpec(BaseModel):
    symbol: str
    name: str
    trading_unit_grams: float
    quote_unit_grams: float
    multiplier_to_10g: float
    purity: float  # Official MCX deliverable purity (fineness parts per 1000)
    problem_statement_purity: float  # Purity as specified in Hack in Hills Problem Statement #03
    tick_size: float
    lot_size_description: str
    exchange: str = "MCX"
    settlement_type: str = "Compulsory Delivery"
    expiry_rule: str
    tender_period_days: int = 3  # Staggered delivery tender period comprises last 3 trading days
    delivery_unit: str
    official_source_url: str = "https://www.mcxindia.com/products/bullion/gold"
    audit_date: str = "2026-10-04"

# Official MCX Gold Contract Specifications
# Audited against https://www.mcxindia.com/products/bullion/gold on 2026-10-04
CONTRACT_SPECS: Dict[str, ContractSpec] = {
    "GOLDM": ContractSpec(
        symbol="GOLDM",
        name="MCX Gold Mini",
        trading_unit_grams=100.0,
        quote_unit_grams=10.0,
        multiplier_to_10g=1.0,  # Quoted per 10 grams
        purity=995.0,           # Official MCX Specification: 995 fineness
        problem_statement_purity=995.0,
        tick_size=1.0,
