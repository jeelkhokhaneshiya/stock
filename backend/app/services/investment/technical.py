from typing import Dict, Any

class TechnicalAnalysisService:
    def evaluate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not data:
            return {"score": 0, "trend": "DATA_UNAVAILABLE"}
            
        rsi = data.get("rsi", 50)
        price = data.get("current_price", 0)
        sma_200 = data.get("sma_200", 0)
        
        score = 50
        if rsi < 30: score += 20
        elif rsi > 70: score -= 20
        
        if price > sma_200 and sma_200 > 0:
            score += 30
            trend = "UPTREND"
        else:
            score -= 20
            trend = "DOWNTREND"
            
        score = max(0, min(100, score))
        return {"score": score, "trend": trend}