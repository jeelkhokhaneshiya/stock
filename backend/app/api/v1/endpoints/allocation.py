from fastapi import APIRouter, Depends, HTTPException
from typing import Any
from app.api import deps
from app.models.user import User
from app.schemas.allocation import AllocationPreviewRequest, PortfolioAllocationReport
from app.services.market_data.factory import get_market_data_service
from app.services.analysis.service import InvestmentAnalysisService
from app.services.allocation.portfolio_analyzer import PortfolioAnalysisService
from app.services.allocation.engine import CapitalAllocationEngine

router = APIRouter()

def get_allocation_engine() -> CapitalAllocationEngine:
    mds = get_market_data_service()
    analysis = InvestmentAnalysisService(mds)
    p_analyzer = PortfolioAnalysisService(mds)
    return CapitalAllocationEngine(analysis, p_analyzer)

@router.post("/{portfolio_id}/allocation-preview", response_model=PortfolioAllocationReport)
def allocation_preview(
    portfolio_id: str,
    request: AllocationPreviewRequest,
    current_user: User = Depends(deps.get_current_user),
    engine: CapitalAllocationEngine = Depends(get_allocation_engine)
) -> Any:
    return engine.generate_preview(request, portfolio_id)
