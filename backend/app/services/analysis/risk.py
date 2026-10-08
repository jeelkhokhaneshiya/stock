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
        debt_to_equity = f_details.get("debt_to_equity", {}).get("value")
        if debt_to_equity is not None and debt_to_equity > 2.0:
            score -= 30
            warnings.append("Excessive debt levels")
            
        # Risk of extreme valuation
        pe_ratio = v_details.get("pe_ratio")
        if isinstance(pe_ratio, dict):
            pe_ratio = pe_ratio.get("value")
        if pe_ratio is not None and pe_ratio > 50:
            score -= 20
            warnings.append("Extreme valuation multiples")
            
        # Risk of poor profitability
        roe = f_details.get("roe", {}).get("value")
        if roe is not None and roe < 0.05 and asset_type == "STOCK":
            score -= 20
            warnings.append("Weak profitability metrics")
            
        # Missing data risk
        missing_count = sum(1 for v in [volatility] if v is None)
        if missing_count > 0:
            score -= (missing_count * 10)
            warnings.append("Incomplete risk data")
            
        return max(0.0, score), details, warnings
