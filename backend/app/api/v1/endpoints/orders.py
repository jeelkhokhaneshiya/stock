from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.broker_order import BrokerOrderRecord

router = APIRouter()

def _verify_portfolio_ownership(db: Session, user_id: int, portfolio_id: str):
    portfolio = db.query(Portfolio).filter(Portfolio.id == int(portfolio_id), Portfolio.user_id == user_id).first()
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found or unauthorized")
    return portfolio

@router.get("/{order_id}")
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = db.query(BrokerOrderRecord).filter(BrokerOrderRecord.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        
    _verify_portfolio_ownership(db, current_user.id, str(order.portfolio_id))
    return {"id": order.id, "status": order.status, "client_order_id": order.client_order_id}

@router.get("/{order_id}/status")
def get_order_status(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = db.query(BrokerOrderRecord).filter(BrokerOrderRecord.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        
    _verify_portfolio_ownership(db, current_user.id, str(order.portfolio_id))
    return {"id": order.id, "status": order.status}

@router.get("/portfolio/{portfolio_id}/history")
def get_order_history(
    portfolio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _verify_portfolio_ownership(db, current_user.id, portfolio_id)
    orders = db.query(BrokerOrderRecord).filter(BrokerOrderRecord.portfolio_id == int(portfolio_id)).order_by(BrokerOrderRecord.created_at.desc()).all()
    return [{"id": o.id, "status": o.status, "client_order_id": o.client_order_id} for o in orders]
