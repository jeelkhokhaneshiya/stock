from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.portfolio import PortfolioCreate, PortfolioResponse

router = APIRouter()

@router.get("", response_model=List[PortfolioResponse])
def read_portfolios(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    portfolios = db.query(Portfolio).filter(Portfolio.user_id == current_user.id).all()
    return portfolios

@router.post("", response_model=PortfolioResponse)
def create_portfolio(
    portfolio_in: PortfolioCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    db_portfolio = Portfolio(
        name=portfolio_in.name,
        base_currency=portfolio_in.base_currency,
        user_id=current_user.id
    )
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio

@router.get("/{portfolio_id}", response_model=PortfolioResponse)
def read_portfolio(
    portfolio_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio
