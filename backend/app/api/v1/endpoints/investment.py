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