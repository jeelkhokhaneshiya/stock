from decimal import Decimal
import math
from typing import Dict, Any
from app.schemas.allocation import RiskProfile
from app.models.enums import AssetType
from app.schemas.analysis import AnalysisReport
from app.services.allocation.config import config

class PositionSizingEngine:
    def calculate_target(
        self,
        analysis: AnalysisReport,
        risk_profile: RiskProfile,
        available_capital: Decimal,
        current_price: Decimal
    ) -> Dict[str, Any]:
        limits = config.RISK_PROFILES[risk_profile]
        
        # Base check for suitability
        if (getattr(analysis, 'long_term_suitability_score', analysis.get('long_term_suitability_score', 0) if isinstance(analysis, dict) else 0) if hasattr(analysis, "long_term_suitability_score") else analysis.get("long_term_suitability_score", 0)) < limits["MIN_SUITABILITY_SCORE"]:
            return {
                "amount": Decimal("0"),
                "percent": Decimal("0"),
                "quantity": Decimal("0"),
                "rejected": True,
                "reason": f"Suitability score {getattr(analysis, 'long_term_suitability_score', analysis.get('long_term_suitability_score', 0) if isinstance(analysis, dict) else 0)} below minimum {limits['MIN_SUITABILITY_SCORE']}"
            }
            
        if analysis.analysis_confidence in ["LOW", "INSUFFICIENT"]:
            return {
                "amount": Decimal("0"),
                "percent": Decimal("0"),
                "quantity": Decimal("0"),
                "rejected": True,
                "reason": f"Analysis confidence {analysis.analysis_confidence} is too low"
            }
            
        # Determine base percentage from score
        # Scale score from min to 100 to a percentage of max allocation
        max_alloc = limits["MAX_SINGLE_STOCK_ALLOCATION"] if analysis.asset_type == AssetType.STOCK else limits["MAX_SINGLE_ASSET_ALLOCATION"]
        
        score_diff = getattr(analysis, 'long_term_suitability_score', analysis.get('long_term_suitability_score', 0) if isinstance(analysis, dict) else 0) - limits["MIN_SUITABILITY_SCORE"]
        range_val = 100.0 - limits["MIN_SUITABILITY_SCORE"]
        
        scale_factor = Decimal(str(score_diff / range_val)) if range_val > 0 else Decimal("0.5")
        
        # We don't want to allocate max immediately. Start conservatively.
        base_alloc = max_alloc * scale_factor
        
        # Reduce if risk is high for this profile
        # Since RiskAnalyzer doesn't output string risk levels strictly yet, we'll map risk_score: 
        # Lower risk score = Better. 
        if getattr(analysis, 'risk_score', analysis.get('risk_score', 0) if isinstance(analysis, dict) else 0) is not None:
            if getattr(analysis, 'risk_score', analysis.get('risk_score', 0) if isinstance(analysis, dict) else 0) < 40: # High Risk
                if "HIGH" not in limits["ALLOWED_RISK"]:
                    return {
                        "amount": Decimal("0"),
                        "percent": Decimal("0"),
                        "quantity": Decimal("0"),
                        "rejected": True,
                        "reason": "Risk level too high for current profile"
                    }
                base_alloc = base_alloc * Decimal("0.5")
                
        target_amount = available_capital * base_alloc
        
        if target_amount < current_price and analysis.asset_type != AssetType.MUTUAL_FUND:
            return {
                "amount": Decimal("0"),
                "percent": Decimal("0"),
                "quantity": Decimal("0"),
                "rejected": True,
                "reason": "Insufficient capital for a single unit"
            }
            
        if analysis.asset_type in [AssetType.STOCK, AssetType.ETF]:
            # Whole units only
            qty = math.floor(target_amount / current_price)
            final_amount = Decimal(str(qty)) * current_price
        else:
            # Mutual funds can be fractional
            qty = target_amount / current_price
            final_amount = target_amount
            
        final_percent = final_amount / available_capital if available_capital > 0 else Decimal("0")
        
        return {
            "amount": final_amount,
            "percent": final_percent,
            "quantity": Decimal(str(qty)),
            "rejected": False,
            "reason": ""
        }
