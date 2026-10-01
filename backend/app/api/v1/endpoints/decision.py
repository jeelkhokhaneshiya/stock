from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api import deps
from app.models.user import User
from app.schemas.decision import DecisionContext, DecisionResponse
from app.services.ai.engine import AIDecisionEngine
from app.services.ai.mock import MockAIProvider
from app.models.decision import DecisionRecord

router = APIRouter()

def get_ai_engine(db: Session = Depends(deps.get_db), mode: str = Query("VALID_BUY", alias="mock_mode")) -> AIDecisionEngine:
    # In a real app we read AI_PROVIDER from env config, here we use Mock for deterministic output
    provider = MockAIProvider(mode=mode)
    return AIDecisionEngine(provider, db)

@router.post("/preview", response_model=DecisionResponse)
def preview_decision(
    context: DecisionContext,
    engine: AIDecisionEngine = Depends(get_ai_engine),
    current_user: User = Depends(deps.get_current_user)
):
    try:
        return engine.evaluate(context)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
@router.get("/{decision_id}", response_model=DecisionResponse)
def get_decision(
    decision_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    record = db.query(DecisionRecord).filter(DecisionRecord.id == decision_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Decision not found")
    return record
