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
            # Contract Identifiers
            "contract_id": contract_id,
            "symbol": symbol,
            "trade_date": record["trade_date"],
            "expiry_date": record["expiry_date"],
            "dte": dte,
            
            # PRESERVED ORIGINAL EXCHANGE PRICES (Zero alteration)
            "raw_close": round(raw_close, 2),
            "raw_open": round(raw_open, 2),
            "raw_high": round(raw_high, 2),
            "raw_low": round(raw_low, 2),
            "close": round(raw_close, 2),  # Backward compatibility
            "open": round(raw_open, 2),
            "high": round(raw_high, 2),
            "low": round(raw_low, 2),
            "volume": volume,
            "open_interest": oi,
            
            # SEPARATED TRADING UNIT & QUOTATION UNIT
            "trading_unit_grams": factors["trading_unit_grams"],
            "quote_unit_grams": factors["quote_unit_grams"],
            "contract_purity": factors["contract_purity"],
            
            # NORMALIZED ANALYTICAL OUTPUTS
            "normalized_close_10g": round(nominal_10g, 2),          # Nominal 10g base
            "purity_adjusted_10g": round(fine_gold_10g, 2),         # 999 Fine Gold Equivalent 10g base
            "fine_gold_price_1g": round(fine_gold_1g, 2),           # 999 Fine Gold per 1g
            "contract_notional_inr": round(contract_notional_inr, 2),# Full contract value in INR
            "implied_basis_pct": round(implied_basis_pct, 4),
            
            # NORMALIZATION AUDIT METADATA
            "quotation_multiplier": factors["quotation_multiplier"],
            "purity_multiplier": round(factors["purity_multiplier"], 6),
            "composite_multiplier": round(factors["composite_multiplier"], 6),
            "reference_basis": f"{factors['reference_weight_grams']}g of {factors['reference_purity']} Fineness Gold"
        }

    def normalize_market_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Batch normalizes market records, dynamically computing near-month benchmark
        to establish basis carry curves.
        """
        if not records:
            return []
            
        df = pd.DataFrame(records)
        
        # Compute benchmark: Near-month GOLDM or nearest active contract per trade_date
        benchmark_map = {}
        for t_date, group in df.groupby("trade_date"):
            goldm_rows = group[group["symbol"] == "GOLDM"].copy()
            if not goldm_rows.empty:
                # Calculate DTE to pick near-month
                goldm_rows["t_dt"] = pd.to_datetime(goldm_rows["trade_date"])
                goldm_rows["e_dt"] = pd.to_datetime(goldm_rows["expiry_date"])
                goldm_rows["dte"] = (goldm_rows["e_dt"] - goldm_rows["t_dt"]).dt.days
                near_goldm = goldm_rows.sort_values("dte").iloc[0]
                norm_res = self.normalize_single_record(near_goldm.to_dict())
                benchmark_map[t_date] = norm_res["purity_adjusted_10g"]
            else:
                # Fallback to group first
                first_row = group.iloc[0].to_dict()
                norm_res = self.normalize_single_record(first_row)
                benchmark_map[t_date] = norm_res["purity_adjusted_10g"]

        normalized_list = []
        for r in records:
            bench = benchmark_map.get(r["trade_date"])
            norm = self.normalize_single_record(r, benchmark_price=bench)
            normalized_list.append(norm)
            
        return normalized_list

    def get_assumptions_report(self) -> Dict[str, Any]:
        """
        Generates comprehensive normalization assumptions documentation.
        """
        specs_report = []
        for sym in ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"]:
            factors = self.get_factors(sym)
            specs_report.append(factors)
            
        guinea_factor = specs_report[2]["purity_multiplier"]
        return {
            "reference_standard": {
                "weight_grams": self.config.reference_weight_grams,
                "purity_fineness": self.config.reference_purity,
                "description": f"Standardized to INR per {self.config.reference_weight_grams}g of {self.config.reference_purity} fine gold equivalent"
            },
            "purity_convention": {
                "active_convention": self.config.purity_convention,
                "GOLDM": "995 Fineness (Official MCX wholesale standard). Purity factor = 999 / 995 ≈ 1.0040201",
                "GOLDTEN": "999 Fineness (Official MCX Circular MCX/TRD/714/2024). Purity factor = 999 / 999 = 1.000000",
                "GOLDGUINEA": (
                    f"{specs_report[2]['contract_purity']} Fineness "
                    f"({'Official MCX deliverable specification' if self.config.purity_convention == 'OFFICIAL_MCX' else 'Problem Statement #03 assumption'}). "
                    f"Purity factor = 999 / {specs_report[2]['contract_purity']} ≈ {guinea_factor:.7f}"
                ),
                "GOLDPETAL": "999 Fineness (Official MCX 1g blister card). Purity factor = 999 / 999 = 1.000000",
                "flagged_assumption": "Problem Statement #03 assumed GOLDGUINEA purity is 999, while official MCX specification is 995 fineness.",
                "notes": self.config.purity_convention_note,
                "mcx_verification": self.config.mcx_verification_note
            },
            "audit_metadata": {
                "audit_date": "2026-10-04",
                "official_source_url": "https://www.mcxindia.com/products/bullion/gold",
                "mcx_circular_references": [
                    "MCX/TRD/714/2024 (Launch of Gold Ten 10g 999 Fineness Futures)",
                    "MCX Gold Mini Product Specification (100g, 995 Fineness, 5th Day Expiry)",
                    "MCX Gold Guinea Product Specification (8g, 995 Fineness, Month-End Expiry)",
