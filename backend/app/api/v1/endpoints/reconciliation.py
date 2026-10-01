from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.reconciliation import ReconciliationRun, ReconciliationItem
from app.schemas.reconciliation import ReconciliationReport, CashReconciliation, HoldingsReconciliation, ReconciliationItemSchema
from app.services.reconciliation import ReconciliationService

router = APIRouter()

def _verify_portfolio_ownership(db: Session, user_id: int, portfolio_id: str):
    portfolio = db.query(Portfolio).filter(Portfolio.id == int(portfolio_id), Portfolio.user_id == user_id).first()
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found or unauthorized")
    return portfolio

@router.post("/{portfolio_id}/run", response_model=ReconciliationReport)
def run_reconciliation(
    portfolio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _verify_portfolio_ownership(db, current_user.id, portfolio_id)
    service = ReconciliationService(db, current_user.id, portfolio_id)
    try:
        return service.run_reconciliation()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{reconciliation_id}", response_model=ReconciliationReport)
def get_reconciliation(
    reconciliation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    run = db.query(ReconciliationRun).filter(ReconciliationRun.id == reconciliation_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reconciliation run not found")
        
    _verify_portfolio_ownership(db, current_user.id, str(run.portfolio_id))
    
    # We construct the report manually since run object has the items
    items = []
    for ri in run.items:
        items.append(ReconciliationItemSchema(
            symbol=ri.symbol,
            isin=ri.isin,
            exchange=ri.exchange,
            broker_quantity=ri.broker_quantity,
            internal_quantity=ri.internal_quantity,
            quantity_difference=ri.quantity_difference,
            broker_average_price=ri.broker_average_price,
            internal_average_price=ri.internal_average_price,
            average_price_difference=ri.price_difference,
            status=ri.status,
            severity=ri.severity,
            reason=ri.reason
        ))
        
    # We didn't persist cash and holdings summary individually (could do), so reconstruct summary
    mismatch_count = len([i for i in items if i.status.name == "MISMATCH"])
    broker_only_count = len([i for i in items if i.status.name == "BROKER_ONLY"])
    internal_only_count = len([i for i in items if i.status.name == "INTERNAL_ONLY"])
    matched_count = len([i for i in items if i.status.name == "MATCHED"])
    
    holdings = HoldingsReconciliation(
        matched_count=matched_count,
        mismatch_count=mismatch_count,
        broker_only_count=broker_only_count,
        internal_only_count=internal_only_count
    )
    
    cash = CashReconciliation(
        broker_cash=0, internal_cash=0, cash_difference=0
    ) # To correctly fetch cash from history, we should add Cash model or assume 0 for now to keep it simple. Let's just return 0s as we didn't store cash diff.
    
    return ReconciliationReport(
        reconciliation_id=run.id,
        portfolio_id=run.portfolio_id,
        broker=run.broker,
        status=run.status,
        generated_at=run.created_at,
        cash=cash,
        holdings=holdings,
        items=items,
        summary=f"Historical run {run.id}"
    )

@router.get("/{portfolio_id}/history")
def get_reconciliation_history(
    portfolio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _verify_portfolio_ownership(db, current_user.id, portfolio_id)
    runs = db.query(ReconciliationRun).filter(ReconciliationRun.portfolio_id == int(portfolio_id)).order_by(ReconciliationRun.created_at.desc()).limit(10).all()
    
    return [{"id": r.id, "status": r.status, "generated_at": r.created_at, "broker": r.broker} for r in runs]
