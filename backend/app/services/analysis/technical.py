from typing import Dict, Any, Tuple, List

class TechnicalAnalyzer:
    def analyze(self, asset_type: str, data: Dict[str, Any]) -> Tuple[float, Dict[str, Any], List[str]]:
        details = {}
        missing = []
        score = 50.0 # base neutral score
        
        # Focus on long-term trends, not intraday
        trend = data.get("long_term_trend")
        if trend:
            details["long_term_trend"] = trend
            if trend == "UP": score += 20
            elif trend == "DOWN": score -= 20
        else:
            missing.append("long_term_trend")
            
        # Drawdown
        max_drawdown = data.get("max_drawdown")
        if max_drawdown is not None:
            details["max_drawdown"] = max_drawdown
            if max_drawdown > 0.30: score -= 20
        else:
            missing.append("max_drawdown")
            
        # RSI as supporting evidence only
        rsi = data.get("rsi_14_weekly")
        if rsi is not None:
            details["rsi_14_weekly"] = rsi
            if rsi < 30: score += 10 # Oversold long term
            elif rsi > 70: score -= 10 # Overbought long term
        else:
            missing.append("rsi_14_weekly")
            
        return max(0.0, min(100.0, score)), details, missing
