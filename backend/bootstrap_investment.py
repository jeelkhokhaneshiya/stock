import os

# Define the file paths and their contents
FILES = {
    "app/models/investment.py": """
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base_class import Base

class Watchlist(Base):
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    symbol = Column(String, index=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(String, nullable=True)

class InvestmentRecommendation(Base):
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    decision = Column(String)  # BUY, HOLD, SELL, WATCHLIST, AVOID
    confidence = Column(Float)
    investment_score = Column(Float)
    risk_level = Column(String)
    reasons = Column(JSON)
    warnings = Column(JSON)
    data_freshness = Column(String)
    review_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class PaperPortfolio(Base):
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    cash = Column(Float, default=1000000.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
class PaperPosition(Base):
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("paperportfolio.id"))
    symbol = Column(String, index=True)
    quantity = Column(Integer)
    average_price = Column(Float)
    current_price = Column(Float, nullable=True)

class PaperTrade(Base):
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("paperportfolio.id"))
    symbol = Column(String, index=True)
    side = Column(String) # BUY / SELL
    quantity = Column(Integer)
    price = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    reason = Column(String, nullable=True)
""",
    
    "app/services/investment/engine.py": """
from typing import Dict, Any

class InvestmentDecisionEngine:
    def __init__(self):
        pass
        
    def evaluate(self, symbol: str, fundamental_data: Dict, technical_data: Dict, current_holdings: Dict = None) -> Dict:
        # Mock deterministic engine for now
        return {
            "symbol": symbol,
            "decision": "WATCHLIST",
            "confidence": 0.8,
            "investment_score": 60.0,
            "risk_level": "MEDIUM",
            "reasons": ["Fundamentals are neutral", "Technical trend is flat"],
            "warnings": [],
            "data_freshness": "FRESH"
        }
""",
    "app/api/v1/endpoints/investment.py": """
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api import deps
from typing import List, Dict

router = APIRouter()

@router.get("/watchlist")
def get_watchlist(db: Session = Depends(deps.get_db)):
    return []

@router.post("/watchlist")
def add_to_watchlist(symbol: str, db: Session = Depends(deps.get_db)):
    return {"status": "added", "symbol": symbol}

@router.get("/analyze/{symbol}")
def analyze_stock(symbol: str, db: Session = Depends(deps.get_db)):
    from app.services.investment.engine import InvestmentDecisionEngine
    engine = InvestmentDecisionEngine()
    return engine.evaluate(symbol, {}, {})
"""
}

def create_files():
    for path, content in FILES.items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.strip())
    print("Files created successfully.")

if __name__ == "__main__":
    create_files()
