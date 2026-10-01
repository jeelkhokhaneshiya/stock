from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Any
from datetime import datetime, timedelta, timezone
from app.api import deps
from app.models.user import User
from app.schemas.market_data import (
    MarketQuote, HistoricalData, CompanyInfo, 
    FundamentalData, ETFInfo, MutualFundInfo
)
from app.services.market_data.factory import get_market_data_service

router = APIRouter()

@router.get("/quote/{symbol}", response_model=MarketQuote)
def get_quote(
    symbol: str,
    exchange: str = "NSE",
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    service = get_market_data_service()
    try:
        return service.get_quote(symbol, exchange)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/history/{symbol}", response_model=HistoricalData)
def get_historical_data(
    symbol: str,
    exchange: str = "NSE",
    timeframe: str = "1d",
    days: int = Query(30, description="Number of past days"),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    service = get_market_data_service()
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        bars = service.get_historical_data(symbol, exchange, timeframe, start_date, end_date)
        
        # Check freshness of the last bar roughly
        is_stale = False
        if bars:
            age = (end_date - bars[-1].timestamp).total_seconds()
            if age > 86400 * 2: # Older than 2 days
                is_stale = True
                
        return HistoricalData(
            data_source=bars[0].data_source if bars else "unknown",
            timestamp=datetime.now(timezone.utc),
            is_stale=is_stale,
            bars=bars
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/company/{symbol}", response_model=CompanyInfo)
def get_company_info(
    symbol: str,
    exchange: str = "NSE",
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    service = get_market_data_service()
    try:
        return service.get_company_info(symbol, exchange)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/fundamentals/{symbol}", response_model=FundamentalData)
def get_fundamentals(
    symbol: str,
    exchange: str = "NSE",
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    service = get_market_data_service()
    try:
        return service.get_fundamentals(symbol, exchange)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/etf/{symbol}", response_model=ETFInfo)
def get_etf_info(
    symbol: str,
    exchange: str = "NSE",
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    service = get_market_data_service()
    try:
        return service.get_etf_info(symbol, exchange)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/mutual-fund/{identifier}", response_model=MutualFundInfo)
def get_mutual_fund_info(
    identifier: str,
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    service = get_market_data_service()
    try:
        return service.get_mutual_fund_info(identifier)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
