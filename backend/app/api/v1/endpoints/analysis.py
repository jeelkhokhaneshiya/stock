from fastapi import APIRouter, Depends, HTTPException
from typing import Any
from app.api import deps
from app.models.user import User
from app.schemas.analysis import AnalysisReport
from app.services.market_data.factory import get_market_data_service
from app.services.analysis.service import InvestmentAnalysisService
from app.models.enums import AssetType

router = APIRouter()

def get_analysis_service() -> InvestmentAnalysisService:
    mds = get_market_data_service()
    return InvestmentAnalysisService(mds)

@router.get("/stock/{symbol}", response_model=AnalysisReport)
def analyze_stock(
    symbol: str,
    exchange: str = "NSE",
    current_user: User = Depends(deps.get_current_user),
    service: InvestmentAnalysisService = Depends(get_analysis_service)
) -> Any:
    try:
        return service.analyze_stock(symbol, exchange)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/etf/{symbol}", response_model=AnalysisReport)
def analyze_etf(
    symbol: str,
    exchange: str = "NSE",
    current_user: User = Depends(deps.get_current_user),
    service: InvestmentAnalysisService = Depends(get_analysis_service)
) -> Any:
    try:
        return service.analyze_etf(symbol, exchange)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/mutual-fund/{identifier}", response_model=AnalysisReport)
def analyze_mutual_fund(
    identifier: str,
    current_user: User = Depends(deps.get_current_user),
    service: InvestmentAnalysisService = Depends(get_analysis_service)
) -> Any:
    try:
        return service.analyze_mutual_fund(identifier)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{asset_type}/{identifier}", response_model=AnalysisReport)
def analyze_generic(
    asset_type: AssetType,
    identifier: str,
    exchange: str = "NSE",
    current_user: User = Depends(deps.get_current_user),
    service: InvestmentAnalysisService = Depends(get_analysis_service)
) -> Any:
    try:
        if asset_type == AssetType.STOCK:
            return service.analyze_stock(identifier, exchange)
        elif asset_type == AssetType.ETF:
            return service.analyze_etf(identifier, exchange)
        elif asset_type == AssetType.MUTUAL_FUND:
            return service.analyze_mutual_fund(identifier)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported asset type for analysis: {asset_type}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
