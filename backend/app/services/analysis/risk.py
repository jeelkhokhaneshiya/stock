from typing import Dict, Any, Tuple, List

class RiskAnalyzer:
    def analyze(self, asset_type: str, data: Dict[str, Any], f_details: Dict[str, Any], v_details: Dict[str, Any]) -> Tuple[float, Dict[str, Any], List[str]]:
        details = {}
        warnings = []
        score = 100.0 # start at low risk (high score = safe)
        
        volatility = data.get("volatility")
        if volatility is not None:
            details["volatility"] = volatility
            if volatility > 0.40:
                score -= 30
                warnings.append("High volatility detected")
                
        # Risk of high debt from fundamentals
        if f_details.get("debt_to_equity", 0) > 2.0:
            score -= 30
            warnings.append("Excessive debt levels")
            
        # Risk of extreme valuation
        if v_details.get("pe_ratio", 0) > 50:
            score -= 20
            warnings.append("Extreme valuation multiples")
            
        # Risk of poor profitability
        if f_details.get("roe", 1.0) < 0.05 and asset_type == "STOCK":
            score -= 20
            warnings.append("Weak profitability metrics")
            
        # Missing data risk
        missing_count = sum(1 for v in [volatility] if v is None)
        if missing_count > 0:
            score -= (missing_count * 10)
            warnings.append("Incomplete risk data")
            
        return max(0.0, score), details, warnings
