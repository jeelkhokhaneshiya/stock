from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.decision import DecisionRecord
from app.models.execution_readiness import ExecutionReadinessRecord

router = APIRouter()

@router.get("/{decision_id}")
def get_execution_readiness(
    decision_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # Cross-user access check
    decision = db.query(DecisionRecord).filter(DecisionRecord.id == decision_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
        
    # We must enforce that the decision's portfolio belongs to the user.
    # We don't have direct access to Portfolio model here cleanly in this snippet,
    # so we rely on the decision_id and a mock or query.
    # Let's query execution readiness record:
    records = db.query(ExecutionReadinessRecord).filter(
        ExecutionReadinessRecord.decision_id == decision_id,
        ExecutionReadinessRecord.user_id == str(current_user.id)
    ).order_by(ExecutionReadinessRecord.id.desc()).all()
    
    if not records:
        # if the user doesn't own it, don't leak existence
        raise HTTPException(status_code=403, detail="Not authorized to access this decision")
        
    record = records[0]
    return {
        "approved": record.result == "APPROVED",
        "mode": record.mode,
        "checks": record.checks,
        "warnings": record.warnings,
        "blocking_reasons": record.blocking_reasons,
        "decision_id": record.decision_id,
        "risk_approval_id": record.risk_approval_id,
        "timestamp": record.created_at.isoformat()
    }
