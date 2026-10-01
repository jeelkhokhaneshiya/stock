from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any
from app.api import deps
from app.models.user import User
from app.models.paper import PaperAccount
from app.schemas.paper import PaperAccountCreate, PaperAccountResponse, OrderRequest, OrderResponse, HoldingResponse
from app.services.paper_broker import PaperBroker

router = APIRouter()

@router.post("/accounts", response_model=PaperAccountResponse)
def create_paper_account(
    req: PaperAccountCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    # Normally check if portfolio belongs to user, simplified here
    acc = PaperAccount(portfolio_id=req.portfolio_id, initial_cash=req.initial_cash, available_cash=req.initial_cash)
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc

@router.get("/accounts/{account_id}", response_model=PaperAccountResponse)
def get_paper_account(
    account_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    acc = db.query(PaperAccount).filter(PaperAccount.id == account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    return acc

@router.post("/accounts/{account_id}/orders/buy", response_model=OrderResponse)
def place_buy_order(
    account_id: int,
    req: OrderRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    broker = deps.get_broker(db, account_id)
    try:
        order = broker.place_buy_order(req.client_order_id, req.symbol, req.quantity, req.price, req.instrument_type)
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/accounts/{account_id}/orders/sell", response_model=OrderResponse)
def place_sell_order(
    account_id: int,
    req: OrderRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    broker = deps.get_broker(db, account_id)
    try:
        order = broker.place_sell_order(req.client_order_id, req.symbol, req.quantity, req.price, req.instrument_type)
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/accounts/{account_id}/orders", response_model=List[OrderResponse])
def get_orders(
    account_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    broker = deps.get_broker(db, account_id)
    return broker.get_orders()

@router.get("/accounts/{account_id}/holdings", response_model=List[HoldingResponse])
def get_holdings(
    account_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    broker = deps.get_broker(db, account_id)
    return broker.get_holdings()

@router.get("/accounts/{account_id}/positions", response_model=List[HoldingResponse])
def get_positions(
    account_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    broker = deps.get_broker(db, account_id)
    return broker.get_positions()
