from decimal import Decimal
from typing import Dict, Any

class AllocationConfig:
    MIN_CASH_RESERVE_PERCENT: Decimal = Decimal("0.05")
    
    # Risk Profile Config
    RISK_PROFILES: Dict[str, Dict[str, Any]] = {
        "CONSERVATIVE": {
            "MAX_SINGLE_STOCK_ALLOCATION": Decimal("0.05"),
            "MAX_SINGLE_ASSET_ALLOCATION": Decimal("0.10"), # For ETFs/Mutual funds
            "MAX_SECTOR_ALLOCATION": Decimal("0.15"),
            "MIN_CASH_RESERVE_PERCENT": Decimal("0.15"),
            "MIN_SUITABILITY_SCORE": 70,
            "ALLOWED_RISK": ["LOW"]
        },
        "MODERATE": {
            "MAX_SINGLE_STOCK_ALLOCATION": Decimal("0.10"),
            "MAX_SINGLE_ASSET_ALLOCATION": Decimal("0.20"),
            "MAX_SECTOR_ALLOCATION": Decimal("0.25"),
            "MIN_CASH_RESERVE_PERCENT": Decimal("0.10"),
            "MIN_SUITABILITY_SCORE": 50,
            "ALLOWED_RISK": ["LOW", "MODERATE"]
        },
        "AGGRESSIVE": {
            "MAX_SINGLE_STOCK_ALLOCATION": Decimal("0.15"),
            "MAX_SINGLE_ASSET_ALLOCATION": Decimal("0.30"),
            "MAX_SECTOR_ALLOCATION": Decimal("0.40"),
            "MIN_CASH_RESERVE_PERCENT": Decimal("0.05"),
            "MIN_SUITABILITY_SCORE": 40,
            "ALLOWED_RISK": ["LOW", "MODERATE", "HIGH"]
        }
    }
    
config = AllocationConfig()
