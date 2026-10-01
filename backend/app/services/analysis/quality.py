from typing import Dict, Any, Tuple, List

class QualityAnalyzer:
    def analyze(self, asset_type: str, data: Dict[str, Any]) -> Tuple[float, Dict[str, Any], List[str]]:
        details = {}
        missing = []
        score = 0.0
        
        # E.g. consistent profitability
        profit_consistent = data.get("profit_consistent_5y")
        if profit_consistent is not None:
            details["profit_consistent_5y"] = profit_consistent
            if profit_consistent: score += 40
        else:
            missing.append("profit_consistent_5y")
            
        moat = data.get("business_moat")
        if moat is not None:
            details["business_moat"] = moat
            if moat == "WIDE": score += 40
            elif moat == "NARROW": score += 20
        else:
            missing.append("business_moat")
            
        management_quality = data.get("management_quality")
        if management_quality is not None:
            details["management_quality"] = management_quality
            if management_quality == "HIGH": score += 20
            
        return min(100.0, score), details, missing
