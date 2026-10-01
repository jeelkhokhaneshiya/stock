from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.schemas.broker import BrokerHealthStatus, BrokerSnapshot
from app.services.broker_sync import BrokerSyncService

router = APIRouter()

def _verify_portfolio_ownership(db: Session, user_id: int, portfolio_id: str):
    portfolio = db.query(Portfolio).filter(Portfolio.id == int(portfolio_id), Portfolio.user_id == user_id).first()
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found or unauthorized")
    return portfolio

@router.get("/status/{portfolio_id}", response_model=BrokerHealthStatus)
def get_broker_status(
    portfolio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _verify_portfolio_ownership(db, current_user.id, portfolio_id)
    service = BrokerSyncService(db, current_user.id, portfolio_id)
    return service.get_status()

@router.get("/portfolio/{portfolio_id}", response_model=BrokerSnapshot)
def get_broker_portfolio(
    portfolio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _verify_portfolio_ownership(db, current_user.id, portfolio_id)
    service = BrokerSyncService(db, current_user.id, portfolio_id)
    try:
        return service.get_snapshot()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
