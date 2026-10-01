from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.shadow import ShadowOrderRecord
from app.models.user import User

router = APIRouter(prefix="/shadow", tags=["Shadow Mode"])

@router.get("/status/{portfolio_id}")
def get_shadow_status(portfolio_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {"portfolio_id": portfolio_id, "mode": "SHADOW", "status": "ACTIVE"}

@router.get("/orders/{portfolio_id}")
def get_shadow_orders(portfolio_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    orders = db.query(ShadowOrderRecord).filter(
        ShadowOrderRecord.portfolio_id == portfolio_id,
        ShadowOrderRecord.user_id == str(current_user.id)
    ).all()
    return orders
