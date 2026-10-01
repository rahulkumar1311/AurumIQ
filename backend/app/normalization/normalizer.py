"""
AurumIQ Contract Normalization Engine
Problem Statement #03: Commodity Derivatives Intelligence

Standardizes MCX Gold futures contracts (GOLDM, GOLDTEN, GOLDGUINEA, GOLDPETAL)
to a common reference: INR per 10 grams of 999 fine-gold-equivalent content.
Separates trading units from quotation units, preserves raw exchange settlement prices,
and provides explicit, configurable purity conventions.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from app.config import CONTRACT_SPECS, NormalizationConfig, DEFAULT_NORMALIZATION_CONFIG

class ContractNormalizationEngine:
    def __init__(self, config: Optional[NormalizationConfig] = None):
        self.config = config or DEFAULT_NORMALIZATION_CONFIG

    def get_factors(self, symbol: str) -> Dict[str, Any]:
        """
        Computes separate quotation scaling and purity adjustment factors for a contract.
        Separates official MCX specifications from problem statement assumptions.
        """
        if symbol not in CONTRACT_SPECS:
            raise ValueError(f"Unknown commodity symbol: {symbol}. Must be one of {list(CONTRACT_SPECS.keys())}")
            
        spec = CONTRACT_SPECS[symbol]
        ref_weight = self.config.reference_weight_grams  # default 10.0g
        ref_purity = self.config.reference_purity        # default 999.0
        
        # Determine effective purity based on active purity convention
        if self.config.purity_convention == "PROBLEM_STATEMENT_03":
            effective_purity = spec.problem_statement_purity
        else:
            effective_purity = spec.purity
            
        # Quotation factor: converts price from quote_unit_grams to reference_weight_grams
        # e.g., 10g / 8g = 1.25 for Guinea; 10g / 1g = 10.0 for Petal
        quotation_multiplier = ref_weight / spec.quote_unit_grams
        
        # Purity factor: converts contract purity to reference fine-gold purity
        # Under OFFICIAL_MCX:
        # GOLDM: 999 / 995 ≈ 1.00402010
        # GOLDTEN: 999 / 999 = 1.00000000
        # GOLDGUINEA: 999 / 995 ≈ 1.00402010
        # GOLDPETAL: 999 / 999 = 1.00000000
        purity_multiplier = ref_purity / effective_purity
        
        # Composite multiplier: quotation_multiplier * purity_multiplier
        composite_multiplier = quotation_multiplier * purity_multiplier
        
        # Trading lot notional multiplier: trading_unit / quote_unit
        # e.g., GOLDM: 100g / 10g = 10; GOLDTEN: 10g / 10g = 1; GUINEA: 8g / 8g = 1; PETAL: 1g / 1g = 1
        notional_multiplier = spec.trading_unit_grams / spec.quote_unit_grams

        is_flagged = (spec.purity != spec.problem_statement_purity)
        assumption_note = (
            f"FLAGGED AUDIT DISCREPANCY: Official MCX deliverable specification is {spec.purity} fineness "
            f"(verified 2026-10-04 from https://www.mcxindia.com/products/bullion/gold), whereas "
            f"Hack in Hills Problem Statement #03 text assumed {spec.problem_statement_purity} purity. "
            f"Active convention: '{self.config.purity_convention}'."
            if is_flagged else "Verified against official MCX product specifications."
        )
        
        return {
            "symbol": symbol,
            "contract_name": spec.name,
            "trading_unit_grams": spec.trading_unit_grams,
            "quote_unit_grams": spec.quote_unit_grams,
            "contract_purity": effective_purity,
            "official_mcx_purity": spec.purity,
            "problem_statement_purity": spec.problem_statement_purity,
            "purity_convention": self.config.purity_convention,
            "is_flagged_assumption": is_flagged,
            "assumption_note": assumption_note,
            "reference_weight_grams": ref_weight,
            "reference_purity": ref_purity,
            "quotation_multiplier": quotation_multiplier,
            "purity_multiplier": purity_multiplier,
            "composite_multiplier": composite_multiplier,
            "notional_multiplier": notional_multiplier,
            "expiry_rule": spec.expiry_rule,
            "tender_period_days": spec.tender_period_days,
            "delivery_unit": spec.delivery_unit,
            "audit_date": spec.audit_date,
            "official_source_url": spec.official_source_url
        }


    def normalize_single_record(
        self,
        record: Dict[str, Any],
        benchmark_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Normalizes a single contract bar while strictly preserving raw exchange settlement prices.
        """
        symbol = record["symbol"]
        factors = self.get_factors(symbol)
        
        raw_close = float(record["close"])
        raw_open = float(record.get("open", raw_close))
        raw_high = float(record.get("high", raw_close))
        raw_low = float(record.get("low", raw_close))
        volume = int(record.get("volume", 0))
        oi = int(record.get("open_interest", 0))
        
        # Parse Dates & DTE
        trade_dt = datetime.strptime(record["trade_date"], "%Y-%m-%d")
        expiry_dt = datetime.strptime(record["expiry_date"], "%Y-%m-%d")
        dte = max(1, (expiry_dt - trade_dt).days)
        
        # 1. Nominal price per reference weight (e.g. 10g) without purity adjustment
        nominal_10g = raw_close * factors["quotation_multiplier"]
        
        # 2. Fine-gold equivalent price per reference weight (e.g. 10g 999 fine gold)
        fine_gold_10g = raw_close * factors["composite_multiplier"]
        
        # 3. Fine-gold price per 1 gram
        fine_gold_1g = fine_gold_10g / factors["reference_weight_grams"]
        
        # 4. Total contract notional value in INR
        contract_notional_inr = raw_close * factors["notional_multiplier"]
        
        # 5. Implied Annualized Basis Rate relative to benchmark spot/near-contract
        implied_basis_pct = 0.0
        if benchmark_price and benchmark_price > 0 and dte > 0:
            implied_basis_pct = ((fine_gold_10g - benchmark_price) / benchmark_price) * (365.0 / dte) * 100.0
            
        contract_id = f"{symbol}_{record['expiry_date']}"

        return {
