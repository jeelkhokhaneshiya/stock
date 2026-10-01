from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any
from app.api.deps import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.models.portfolio import Portfolio
from app.models.paper import PaperAccount, PaperHolding
from app.models.autonomous import AutonomousCycleRecord
from app.models.execution import ExecutionRecord
from app.schemas.autonomous import AutonomousCycleResponse, AutonomousExecutionResponse, AutonomousStatusResponse, AutonomousCycleResult
from app.core.config import settings
from app.services.market_session import MarketSessionService
from app.services.universe_provider import MockInvestmentUniverseProvider
from app.services.market_data.mock_provider import MockMarketDataProvider
from app.services.analysis.fundamental import FundamentalAnalyzer
from app.services.analysis.technical import TechnicalAnalyzer
from app.services.analysis.valuation import ValuationAnalyzer
from app.services.analysis.quality import QualityAnalyzer
from app.services.analysis.risk import RiskAnalyzer
from app.services.analysis.service import InvestmentAnalysisService
from app.services.allocation.portfolio_analyzer import PortfolioAnalysisService
from app.services.allocation.position_sizing import PositionSizingEngine
from app.services.allocation.diversification import DiversificationEngine
from app.services.allocation.engine import CapitalAllocationEngine
from app.services.ai.mock import MockAIProvider
from app.services.ai.engine import AIDecisionEngine
from app.services.risk.engine import RiskApprovalEngine
from app.services.execution_service import ExecutionService
from app.services.autonomous_manager import AutonomousPortfolioManager

router = APIRouter()

def get_autonomous_manager(db: Session = Depends(get_db)) -> AutonomousPortfolioManager:
    market_session = MarketSessionService()
    universe_provider = MockInvestmentUniverseProvider()
    market_data_service = MockMarketDataProvider()
    
    inv_analysis = InvestmentAnalysisService(
        market_data_service=market_data_service
    )
    
    portfolio_analyzer = PortfolioAnalysisService(market_data_service=market_data_service)
    diversification = DiversificationEngine()
    position_sizing = PositionSizingEngine()
    
    cap_alloc = CapitalAllocationEngine(
        analysis_service=inv_analysis,
        p_analyzer=portfolio_analyzer
    )
    
    ai_provider = MockAIProvider()
    ai_decision = AIDecisionEngine(db=db, provider=ai_provider)
    
    risk_approval = RiskApprovalEngine(db=db)
    exec_service = ExecutionService(db=db)
    
    return AutonomousPortfolioManager(
        db=db,
        market_session=market_session,
        universe_provider=universe_provider,
        market_data_service=market_data_service,
        investment_analysis=inv_analysis,
        portfolio_analysis=portfolio_analyzer,
        capital_allocation=cap_alloc,
        ai_decision=ai_decision,
        risk_approval=risk_approval,
        execution_service=exec_service
    )

@router.post("/cycle/{portfolio_id}", response_model=AutonomousCycleResult)
def trigger_cycle(
    portfolio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    manager: AutonomousPortfolioManager = Depends(get_autonomous_manager)
):
    if not settings.AUTONOMOUS_MODE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Autonomous mode is disabled")
        
    portfolio = db.query(Portfolio).filter(Portfolio.id == int(portfolio_id), Portfolio.user_id == current_user.id).first()
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
        
    result = manager.execute_cycle(portfolio_id)
    return result

@router.get("/cycle/{cycle_id}", response_model=AutonomousCycleResponse)
def get_cycle(
    cycle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cycle = db.query(AutonomousCycleRecord).filter(AutonomousCycleRecord.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found")
        
    portfolio = db.query(Portfolio).filter(Portfolio.id == int(cycle.portfolio_id), Portfolio.user_id == current_user.id).first()
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this cycle")
        
    # Build response
    resp = cycle.summary or {}
    resp["started_at"] = cycle.started_at
    resp["completed_at"] = cycle.completed_at
    return resp

@router.get("/cycle/{cycle_id}/executions", response_model=List[AutonomousExecutionResponse])
def get_cycle_executions(
    cycle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cycle = db.query(AutonomousCycleRecord).filter(AutonomousCycleRecord.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found")
        
    portfolio = db.query(Portfolio).filter(Portfolio.id == int(cycle.portfolio_id), Portfolio.user_id == current_user.id).first()
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view these executions")
        
    summary = cycle.summary or {}
    exec_ids = summary.get("execution_ids", [])
    
    executions = db.query(ExecutionRecord).filter(ExecutionRecord.id.in_(exec_ids)).all()
    return executions

@router.get("/status/{portfolio_id}", response_model=AutonomousStatusResponse)
def get_autonomous_status(
    portfolio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    portfolio = db.query(Portfolio).filter(Portfolio.id == int(portfolio_id), Portfolio.user_id == current_user.id).first()
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
        
    account = db.query(PaperAccount).filter(PaperAccount.portfolio_id == portfolio.id).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper account not found")
        
    last_cycle = db.query(AutonomousCycleRecord).filter(
        AutonomousCycleRecord.portfolio_id == portfolio_id
    ).order_by(AutonomousCycleRecord.started_at.desc()).first()
    
    holdings = db.query(PaperHolding).filter(PaperHolding.paper_account_id == account.id).all()
    
    market_session = MarketSessionService()
    
    # Calculate portfolio value
    port_val = account.available_cash
    for h in holdings:
        port_val += (h.quantity * h.average_price) # MOCK
    
    return AutonomousStatusResponse(
        portfolio_id=portfolio_id,
        autonomous_mode=settings.AUTONOMOUS_MODE,
        broker_mode="PAPER",
        market_status=market_session.get_market_status(),
        last_cycle_id=last_cycle.id if last_cycle else None,
        last_cycle_status=last_cycle.status if last_cycle else None,
        last_cycle_at=last_cycle.started_at if last_cycle else None,
        current_cash=account.available_cash,
        portfolio_value=port_val,
        holding_count=len(holdings),
        last_error=last_cycle.summary.get("errors", [""])[0] if last_cycle and last_cycle.summary and last_cycle.summary.get("errors") else None
    )
