import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock

from sqlalchemy.orm import Session

from app.services.execution_readiness import ExecutionReadinessService
from app.models.decision import DecisionRecord
from app.models.risk import RiskApprovalRecord
from app.models.enums import AssetType
from app.core.config import settings

def test_1000_safety_case(db_session: Session):
    service = ExecutionReadinessService(db_session)
    
    user_id = "user1"
    portfolio_id = "port1"
    
    # Starting cash ?1,000
    starting_cash = Decimal("1000")
    
    # decision 1 BUY ?700
    dec1 = DecisionRecord(portfolio_id=portfolio_id, symbol="ABC", asset_type=AssetType.STOCK, decision="BUY", confidence=0.8, risk_level="LOW", analysis_score=8.0, allocation_amount=Decimal("700"), allocation_percent=Decimal("70"), recommended_quantity=Decimal("7"), reason="Test", supporting_factors={}, risk_factors={}, reassessment_conditions={}, prompt_version="1", model_name="test")
    db_session.add(dec1)
    db_session.commit()
    
    risk1 = RiskApprovalRecord(decision_id=dec1.id, portfolio_id=portfolio_id, symbol="ABC", asset_type=AssetType.STOCK, original_decision="BUY", final_status="APPROVED", execution_intent="DELIVERY_LONG_TERM", requested_amount=Decimal("700"), approved_amount=Decimal("700"), requested_quantity=Decimal("7"), approved_quantity=Decimal("7"), risk_profile="LOW", checks={}, warnings={}, rejection_reasons={}, modifications={})
    db_session.add(risk1)
    db_session.commit()
    
    res1 = service.evaluate_readiness(user_id, portfolio_id, dec1.id, Decimal("100"), "mock", 10, starting_cash, {})
    assert res1.approved == True
    
    # Assume it executes, remaining cash = 300
    current_cash = Decimal("300")
    
    # decision 2 BUY ?400
    dec2 = DecisionRecord(portfolio_id=portfolio_id, symbol="XYZ", asset_type=AssetType.STOCK, decision="BUY", confidence=0.8, risk_level="LOW", analysis_score=8.0, allocation_amount=Decimal("400"), allocation_percent=Decimal("40"), recommended_quantity=Decimal("4"), reason="Test", supporting_factors={}, risk_factors={}, reassessment_conditions={}, prompt_version="1", model_name="test")
    db_session.add(dec2)
    db_session.commit()
    
    risk2 = RiskApprovalRecord(decision_id=dec2.id, portfolio_id=portfolio_id, symbol="XYZ", asset_type=AssetType.STOCK, original_decision="BUY", final_status="APPROVED", execution_intent="DELIVERY_LONG_TERM", requested_amount=Decimal("400"), approved_amount=Decimal("400"), requested_quantity=Decimal("4"), approved_quantity=Decimal("4"), risk_profile="LOW", checks={}, warnings={}, rejection_reasons={}, modifications={})
    db_session.add(risk2)
    db_session.commit()
    
    res2 = service.evaluate_readiness(user_id, portfolio_id, dec2.id, Decimal("100"), "mock", 10, current_cash, {})
    assert res2.approved == False
    assert "INSUFFICIENT_CASH" in res2.blocking_reasons

def test_angel_one_zero_calls(monkeypatch, db_session: Session):
    import requests
    def mock_post(*args, **kwargs):
        raise RuntimeError("REAL BROKER API CALLED")
    
    monkeypatch.setattr(requests, "post", mock_post)
    
    service = ExecutionReadinessService(db_session)
    # mock a valid execution check
    res = service.evaluate_readiness("user1", "port1", 9999, Decimal("100"), "mock", 10, Decimal("1000"), {})
    
    # Asserting that no error was raised!
    assert res.approved == False # Will be blocked due to decision missing, but no HTTP called
