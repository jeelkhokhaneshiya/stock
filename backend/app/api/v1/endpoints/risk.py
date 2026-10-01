from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.models.user import User
from app.schemas.risk import RiskApprovalRequest, RiskApprovalResult
from app.services.risk.engine import RiskApprovalEngine
from app.models.risk import RiskApprovalRecord

router = APIRouter()

def get_risk_engine(db: Session = Depends(deps.get_db)) -> RiskApprovalEngine:
    return RiskApprovalEngine(db)

@router.post("/approve", response_model=RiskApprovalResult)
def approve_decision(
    request: RiskApprovalRequest,
    engine: RiskApprovalEngine = Depends(get_risk_engine),
    current_user: User = Depends(deps.get_current_user)
):
    try:
        return engine.evaluate(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
@router.get("/{approval_id}", response_model=RiskApprovalResult)
def get_approval(
    approval_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    record = db.query(RiskApprovalRecord).filter(RiskApprovalRecord.id == approval_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Approval not found")
    return RiskApprovalResult(
        id=record.id,
        status=record.final_status,
        decision=record.original_decision,
        execution_intent=record.execution_intent,
        requested_amount=record.requested_amount,
        approved_amount=record.approved_amount,
        requested_quantity=record.requested_quantity,
        approved_quantity=record.approved_quantity,
        checks=record.checks,
        warnings=record.warnings,
        rejection_reasons=record.rejection_reasons,
        modifications=record.modifications
    )
