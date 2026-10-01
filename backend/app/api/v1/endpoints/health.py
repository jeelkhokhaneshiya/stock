from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.api import deps
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/health")
def health_check(db: Session = Depends(deps.get_db)):
    try:
        # Simple DB check
        db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Database unavailable")
    
    return {"status": "ok", "message": "Service is healthy", "database": "connected"}

@router.get("/ready")
def readiness_check(db: Session = Depends(deps.get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Readiness check failed (DB): {str(e)}")
        raise HTTPException(status_code=503, detail="Not ready: Database unavailable")
    
    from app.core.config import settings
    
    if settings.ENABLE_LIVE_TRADING or settings.LIVE_EXECUTION_UNLOCKED or not getattr(settings, 'BROKER_EXECUTION_BLOCKED', True):
        raise HTTPException(
            status_code=503, 
            detail="Not ready: Safety flags invalid. Live trading is currently unsupported and must be explicitly disabled."
        )

    return {
        "status": "ready",
        "safety_checks": {
            "ENABLE_LIVE_TRADING": settings.ENABLE_LIVE_TRADING,
            "LIVE_EXECUTION_UNLOCKED": settings.LIVE_EXECUTION_UNLOCKED,
            "BROKER_EXECUTION_BLOCKED": getattr(settings, 'BROKER_EXECUTION_BLOCKED', True)
        }
    }
