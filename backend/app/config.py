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
