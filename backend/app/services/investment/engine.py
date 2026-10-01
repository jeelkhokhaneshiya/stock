from typing import Dict, Any
from datetime import datetime, timedelta
from app.services.investment.fundamental import FundamentalAnalysisService
from app.services.investment.valuation import ValuationService
from app.services.investment.technical import TechnicalAnalysisService
from app.services.investment.risk import RiskAnalysisService

class InvestmentDecisionEngine:
    def __init__(self):
        self.fundamental = FundamentalAnalysisService()
        self.valuation = ValuationService()
        self.technical = TechnicalAnalysisService()
        self.risk = RiskAnalysisService()

    def evaluate(self, symbol: str, data: Dict[str, Any], current_position: Dict = None) -> Dict[str, Any]:
        fund_res = self.fundamental.evaluate(data)
        val_res = self.valuation.evaluate(data)
        tech_res = self.technical.evaluate(data)
        risk_res = self.risk.evaluate(data)
        
        # Weighted Score
        inv_score = (
            fund_res["score"] * 0.4 +
            val_res["score"] * 0.2 +
            tech_res["score"] * 0.2 +
            risk_res["score"] * 0.2
        )
        
        reasons = []
        decision = "WATCHLIST"
        
        if current_position:
            # PROFIT REVIEW LOGIC
            pnl_percent = current_position.get("pnl_percent", 0)
            if pnl_percent > 20:
                if fund_res["score"] < 50 or val_res["classification"] == "VERY_EXPENSIVE":
                    decision = "SELL REVIEW"
                    reasons.append("Profit threshold reached, but fundamentals/valuation deteriorating.")
                else:
                    decision = "HOLD"
                    reasons.append("20% profit reached, but thesis remains strong. Holding for further upside.")
            elif pnl_percent < 0:
                if fund_res["score"] < 40 or risk_res["level"] == "VERY_HIGH":
                    decision = "EXIT REVIEW"
                    reasons.append("Loss-making position with materially deteriorating fundamentals or extreme risk.")
                else:
                    decision = "HOLD / REVIEW"
                    reasons.append("Position is at a loss, but company remains fundamentally strong. Avoid panic selling.")
            else:
                if fund_res["score"] < 40:
                    decision = "SELL REVIEW"
                    reasons.append("Fundamentals deteriorating.")
                else:
                    decision = "HOLD"
                    reasons.append("Thesis remains intact.")
        else:
            if inv_score >= 70 and risk_res["level"] in ["LOW", "MEDIUM"]:
                decision = "BUY"
                reasons.append("Strong fundamentals and acceptable risk.")
            elif inv_score < 40:
                decision = "AVOID"
                reasons.append("Poor investment score.")
            else:
                decision = "WATCHLIST"
                reasons.append("Neutral indicators.")
                
        return {
            "symbol": symbol,
            "decision": decision,
            "confidence": 0.85,
            "investment_score": round(inv_score, 2),
            "risk_level": risk_res["level"],
            "reasons": reasons,
            "fundamental_rating": fund_res["rating"],
            "valuation_rating": val_res["classification"],
            "technical_trend": tech_res["trend"],
            "data_freshness": "FRESH" if data else "UNAVAILABLE",
            "review_date": (datetime.utcnow() + timedelta(days=30)).isoformat()
        }