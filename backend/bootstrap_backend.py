import os

BACKEND_FILES = {
    "app/services/investment/fundamental.py": """
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
""",

    "app/services/investment/valuation.py": """
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
""",

    "app/services/investment/technical.py": """
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
""",

    "app/services/investment/risk.py": """
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
""",

    "app/services/investment/engine.py": """
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
                    reasons.append("20% profit reached, but thesis remains strong.")
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
""",

    "app/services/market_data_provider.py": """
from typing import Dict, Any

class MockMarketDataProvider:
    def get_stock_data(self, symbol: str) -> Dict[str, Any]:
        # Return mock data based on symbol to provide deterministic test cases
        if "HDFCBANK" in symbol:
            return {"roe": 16, "debt_to_equity": 0.8, "pe_ratio": 18, "pb_ratio": 3, "rsi": 45, "current_price": 1600, "sma_200": 1500, "volatility": 0.2}
        if "WEAK" in symbol:
            return {"roe": 5, "debt_to_equity": 2.5, "pe_ratio": 60, "pb_ratio": 8, "rsi": 20, "current_price": 10, "sma_200": 50, "volatility": 0.6}
        return {"roe": 12, "debt_to_equity": 1.2, "pe_ratio": 22, "pb_ratio": 4, "rsi": 55, "current_price": 100, "sma_200": 90, "volatility": 0.3}
""",

    "app/api/v1/endpoints/investment.py": """
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api import deps
from typing import List, Dict
from app.services.investment.engine import InvestmentDecisionEngine
from app.services.market_data_provider import MockMarketDataProvider
from app.models.investment import Watchlist, PaperPortfolio, PaperTrade

router = APIRouter()
engine = InvestmentDecisionEngine()
provider = MockMarketDataProvider()

@router.get("/watchlist")
def get_watchlist(db: Session = Depends(deps.get_db)):
    # Mock return for UI demo
    return [{"symbol": "HDFCBANK"}, {"symbol": "INFY"}]

@router.get("/analyze/{symbol}")
def analyze_stock(symbol: str, db: Session = Depends(deps.get_db)):
    data = provider.get_stock_data(symbol)
    return engine.evaluate(symbol, data)

@router.post("/paper-trade")
def execute_paper_trade(symbol: str, side: str, quantity: int, db: Session = Depends(deps.get_db)):
    data = provider.get_stock_data(symbol)
    price = data.get("current_price", 0)
    trade = PaperTrade(symbol=symbol, side=side, quantity=quantity, price=price, reason="User initiated")
    db.add(trade)
    db.commit()
    return {"status": "success", "trade_id": trade.id}
    
@router.get("/portfolio-analysis")
def portfolio_analysis(db: Session = Depends(deps.get_db)):
    # Mocking read-only portfolio analysis
    return {
        "total_invested": 50000,
        "current_value": 65000,
        "pnl_percent": 30.0,
        "holdings": [
            engine.evaluate("HDFCBANK", provider.get_stock_data("HDFCBANK"), current_position={"pnl_percent": 35.0})
        ]
    }
"""
}

def create_backend_files():
    for path, content in BACKEND_FILES.items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.strip())
    print("Backend investment modules created successfully.")

if __name__ == "__main__":
    create_backend_files()
