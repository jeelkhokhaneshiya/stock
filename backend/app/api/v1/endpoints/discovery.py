from fastapi import APIRouter, Depends
from typing import Any
from app.api import deps
from app.models.user import User
from app.services.discovery.scanner import MarketScanner

router = APIRouter()

@router.get("/candidates")
def discover_candidates(
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    Run the automatic market discovery pipeline to find top investment candidates.
    """
    scanner = MarketScanner()
    return scanner.discover_opportunities()
