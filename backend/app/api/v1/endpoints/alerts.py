from fastapi import APIRouter
from typing import Any, Dict, List
from app.services.portfolio.alert_engine import get_alert_engine

router = APIRouter()

@router.get("/")
def get_alerts() -> List[Dict[str, Any]]:
    return get_alert_engine().get_recent_alerts()
