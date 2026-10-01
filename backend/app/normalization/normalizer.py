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
