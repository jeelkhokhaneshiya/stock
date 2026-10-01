from typing import Dict, Any

class FundamentalAnalysisService:
    def evaluate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not data:
            return {"score": 0, "rating": "DATA_UNAVAILABLE"}
        
        roe = data.get("roe", 0)
        debt_to_equity = data.get("debt_to_equity", 100)
        
        score = 50
        if roe > 15: score += 25
        elif roe > 10: score += 10
        else: score -= 10
        
        if debt_to_equity < 0.5: score += 25
        elif debt_to_equity < 1: score += 10
        else: score -= 20
        
        score = max(0, min(100, score))
        
        if score >= 80: rating = "Strong"
        elif score >= 65: rating = "Good"
        elif score >= 50: rating = "Neutral"
        elif score >= 35: rating = "Weak"
        else: rating = "Very Weak"
        
        return {"score": score, "rating": rating}