from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict
from app.services.portfolio.portfolio_manager import PortfolioManager
from app.services.portfolio.alert_engine import get_alert_engine

router = APIRouter()

from app.api.deps import get_angel_one_data_service
from app.services.brokers.angel_one.data_service import AngelOneDataService

def get_portfolio_manager(client: AngelOneDataService = Depends(get_angel_one_data_service)):
    return PortfolioManager(client=client)

@router.get("/analysis")
def get_portfolio_analysis(manager: PortfolioManager = Depends(get_portfolio_manager)) -> Dict[str, Any]:
    res = manager.get_full_portfolio_analysis()
    return res

@router.get("/holdings-analysis")
def get_holdings_analysis(manager: PortfolioManager = Depends(get_portfolio_manager)) -> Dict[str, Any]:
    res = manager.get_full_portfolio_analysis()
    if res.get("status") == "BROKER_DISCONNECTED":
        return res
    return {"holdings_analysis": res.get("holdings_analysis", [])}

@router.get("/buy-candidates")
def get_buy_candidates(manager: PortfolioManager = Depends(get_portfolio_manager)) -> Dict[str, Any]:
    res = manager.get_full_portfolio_analysis()
    if res.get("status") == "BROKER_DISCONNECTED":
        return res
    return {"buy_candidates": res.get("buy_candidates", [])}

@router.get("/sell-review")
def get_sell_review(manager: PortfolioManager = Depends(get_portfolio_manager)) -> Dict[str, Any]:
    res = manager.get_full_portfolio_analysis()
    if res.get("status") == "BROKER_DISCONNECTED":
        return res
    return {"sell_review": res.get("sell_review", [])}

@router.get("/watchlist")
def get_watchlist(manager: PortfolioManager = Depends(get_portfolio_manager)) -> Dict[str, Any]:
    res = manager.get_full_portfolio_analysis()
    if res.get("status") == "BROKER_DISCONNECTED":
        return res
    return {"watchlist": res.get("watchlist", [])}

@router.get("/risk")
def get_risk_summary(manager: PortfolioManager = Depends(get_portfolio_manager)) -> Dict[str, Any]:
    res = manager.get_full_portfolio_analysis()
    if res.get("status") == "BROKER_DISCONNECTED":
        return res
    return {"risk_summary": res.get("risk_summary", {})}
