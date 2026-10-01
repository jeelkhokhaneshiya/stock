import pytest
from app.services.ai.engine import AIDecisionEngine
from app.services.ai.mock import MockAIProvider
from app.schemas.decision import DecisionContext
from sqlalchemy.orm import Session
import json
from unittest.mock import MagicMock

def test_ai_hallucinated_quantity(db_session: Session):
    class HallucinatingAI(MockAIProvider):
        def generate_decision(self, prompt, context):
            # Returns an arbitrary un-approved quantity
            return json.dumps({
                "decision": "BUY",
                "confidence": 0.9,
                "risk_level": "LOW",
                "recommended_amount": 999999,
                "recommended_allocation_percent": 100.0,
                "recommended_quantity": 9999,
                "reason": "AI loves it",
                "supporting_factors": [],
                "risk_factors": [],
                "reassessment_conditions": []
            })
            
    engine = AIDecisionEngine(HallucinatingAI(), db_session)
    
    # But alloc only allows 500
    context = DecisionContext(
        portfolio_id="p1",
        symbol="XYZ",
        asset_type="STOCK",
        available_capital=1000.0, risk_profile="MODERATE", investment_horizon="LONG_TERM",
        current_holdings={},
        market_data={},
        analysis_report={"analysis_confidence": "HIGH", "long_term_suitability_score": 90, "risk_score": 90},
        allocation_recommendation={"allocation_amount": 500, "allocation_percent": 50.0}
    )
    
    res = engine.evaluate(context)
    # AI hallucinated 999999, but engine bounds it to 500
    assert res.allocation_amount == 500
    assert "Amount bounded by allocation limits" in res.reason

def test_ai_buy_with_insufficient_analysis(db_session: Session):
    class StubbornAI(MockAIProvider):
        def generate_decision(self, prompt, context):
            return json.dumps({
                "decision": "BUY",
                "confidence": 0.9,
                "risk_level": "LOW",
                "recommended_amount": 500,
                "recommended_allocation_percent": 50.0,
                "recommended_quantity": 5,
                "reason": "I ignore your rules",
                "supporting_factors": [],
                "risk_factors": [],
                "reassessment_conditions": []
            })
            
    engine = AIDecisionEngine(StubbornAI(), db_session)
    
    context = DecisionContext(
        portfolio_id="p1",
        symbol="XYZ",
        asset_type="STOCK",
        available_capital=1000.0, risk_profile="MODERATE", investment_horizon="LONG_TERM",
        current_holdings={},
        market_data={},
        analysis_report={"analysis_confidence": "INSUFFICIENT", "long_term_suitability_score": 10, "risk_score": 10},
        allocation_recommendation={"allocation_amount": 500, "allocation_percent": 50.0}
    )
    
    res = engine.evaluate(context)
    # The guardrail should intercept and return AVOID
    assert res.decision == "AVOID"
    assert res.allocation_amount == 0
