from typing import Dict, Any

class ValuationService:
    def evaluate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not data:
            return {"score": 0, "classification": "DATA_UNAVAILABLE"}
            
        pe_ratio = data.get("pe_ratio", None)
        pb_ratio = data.get("pb_ratio", None)
        
        if pe_ratio is None:
            return {"score": 0, "classification": "DATA_UNAVAILABLE"}
            
        score = 50
        if pe_ratio < 15: 
            score = 80
            classification = "UNDERVALUED"
        elif pe_ratio < 25: 
            score = 60
            classification = "FAIRLY_VALUED"
        elif pe_ratio < 40: 
            score = 30
            classification = "EXPENSIVE"
        else: 
            score = 10
            classification = "VERY_EXPENSIVE"
            
        return {"score": score, "classification": classification}