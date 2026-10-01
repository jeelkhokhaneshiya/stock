from typing import Dict, Any

class RiskAnalysisService:
    def evaluate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not data:
            return {"score": 0, "level": "DATA_UNAVAILABLE"}
            
        volatility = data.get("volatility", 0) # 0 to 1
        
        if volatility > 0.4:
            score = 20
            level = "VERY_HIGH"
        elif volatility > 0.25:
            score = 40
            level = "HIGH"
        elif volatility > 0.15:
            score = 70
            level = "MEDIUM"
        else:
            score = 90
            level = "LOW"
            
        return {"score": score, "level": level}