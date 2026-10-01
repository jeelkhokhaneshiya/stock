from decimal import Decimal
from typing import Dict, Any, List
from app.schemas.allocation import PortfolioAnalysisReport
from app.services.allocation.config import config
from app.schemas.allocation import RiskProfile
from app.models.enums import AssetType

class DiversificationEngine:
    def check_limits(
        self, 
        symbol: str, 
        asset_type: AssetType, 
        sector: str,
        current_portfolio: PortfolioAnalysisReport,
        risk_profile: RiskProfile,
        proposed_additional_amount: Decimal
    ) -> Dict[str, Any]:
        limits = config.RISK_PROFILES[risk_profile]
        
        max_single_alloc = limits["MAX_SINGLE_STOCK_ALLOCATION"] if asset_type == AssetType.STOCK else limits["MAX_SINGLE_ASSET_ALLOCATION"]
        
        total_value = current_portfolio.total_portfolio_value + proposed_additional_amount
        
        # Check current single exposure
        current_exposure = Decimal("0")
        for h in current_portfolio.holdings:
            if h.symbol == symbol:
                current_exposure = h.market_value
                break
                
        new_exposure = current_exposure + proposed_additional_amount
        new_exposure_pct = new_exposure / total_value if total_value > 0 else Decimal("0")
        
        if new_exposure_pct > max_single_alloc:
            return {
                "allowed": False,
                "reason": f"Exceeds maximum single position allocation of {max_single_alloc:.1%}"
            }
            
        return {
            "allowed": True,
            "reason": "Within diversification limits"
        }
