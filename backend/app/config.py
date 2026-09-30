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
        lot_size_description="100 grams (10 x 10g units, 995 fineness)",
        expiry_rule="5th day of the contract expiry month (or preceding business day if holiday)",
        tender_period_days=3,
        delivery_unit="100 grams bar"
    ),
    "GOLDTEN": ContractSpec(
        symbol="GOLDTEN",
        name="MCX Gold Ten",
        trading_unit_grams=10.0,
        quote_unit_grams=10.0,
        multiplier_to_10g=1.0,  # Quoted per 10 grams
        purity=999.0,           # Official MCX Circular MCX/TRD/714/2024: 999 fineness
        problem_statement_purity=999.0,
        tick_size=0.5,
        lot_size_description="10 grams (999 fineness)",
        expiry_rule="Last calendar day of the contract expiry month (or preceding business day if holiday)",
        tender_period_days=3,
        delivery_unit="10 grams bar/coin"
    ),
    "GOLDGUINEA": ContractSpec(
        symbol="GOLDGUINEA",
        name="MCX Gold Guinea",
        trading_unit_grams=8.0,
        quote_unit_grams=8.0,
        multiplier_to_10g=10.0 / 8.0,  # Quoted per 8g (1 Guinea) -> x1.25 for 10g
        purity=995.0,           # Official MCX Specification: 995 fineness coin standard
        problem_statement_purity=999.0, # Flagged assumption: PS#03 stated 999 purity
        tick_size=1.0,
        lot_size_description="8 grams (1 Guinea coin, 995 fineness)",
        expiry_rule="Last calendar day of the contract expiry month (or preceding business day if holiday)",
        tender_period_days=3,
        delivery_unit="8 grams coin"
    ),
    "GOLDPETAL": ContractSpec(
        symbol="GOLDPETAL",
        name="MCX Gold Petal",
        trading_unit_grams=1.0,
        quote_unit_grams=1.0,
        multiplier_to_10g=10.0,  # Quoted per 1g -> x10 for 10g
        purity=999.0,           # Official MCX Specification: 999 fineness
        problem_statement_purity=999.0,
        tick_size=1.0,
        lot_size_description="1 gram (999 fineness blister card)",
        expiry_rule="Last calendar day of the contract expiry month (or preceding business day if holiday)",
        tender_period_days=3,
        delivery_unit="1 gram blister card"
    )
}

# Transaction Cost Parameters (MCX Standard Regulatory Structure)
MCX_TURNOVER_FEE_PCT = 0.0015  # 0.0015% (~ ₹150 per crore)
CTT_SELL_PCT = 0.01            # Commodity Transaction Tax on sell side: 0.01%
STAMP_DUTY_BUY_PCT = 0.002     # Stamp duty on buy side: 0.002%
BROKERAGE_PCT = 0.005          # 0.005% institutional brokerage
GST_PCT = 18.0                 # 18% on (Brokerage + Exchange fees)

class NormalizationConfig(BaseModel):
    reference_weight_grams: float = 10.0
    reference_purity: float = 999.0  # Fine gold equivalent (999 parts per 1000)
    purity_convention: str = "OFFICIAL_MCX"  # "OFFICIAL_MCX" (GOLDGUINEA=995) or "PROBLEM_STATEMENT_03" (GOLDGUINEA=999)
    allow_raw_purity_mode: bool = True
    tender_buffer_days: int = 3  # MCX staggered delivery tender window (last 3 trading days)
