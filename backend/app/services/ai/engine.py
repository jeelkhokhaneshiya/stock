from typing import Dict, Any, Tuple
import json
import logging
from sqlalchemy.orm import Session
from app.schemas.decision import DecisionContext, DecisionRecommendation, DecisionResponse
from app.models.decision import DecisionRecord
from app.services.ai.provider import AIProvider
from app.services.ai.mock import MockAIProvider

logger = logging.getLogger(__name__)

DECISION_PROMPT_VERSION = "v1"

class AIDecisionEngine:
    def __init__(self, provider: AIProvider, db: Session):
        self.provider = provider
        self.db = db
        
    def _build_prompt(self, context: DecisionContext) -> str:
        return f"""
        You are an AI Investment Decision Engine (Version {DECISION_PROMPT_VERSION}).
        Your role is to evaluate long-term investment opportunities based on the provided context.
        You must return a valid JSON matching the DecisionRecommendation schema.
        
        ALLOWED DECISIONS: BUY, HOLD, ADD, REDUCE, SELL, AVOID.
        
        RULES:
        - Do not predict the future or guarantee returns.
        - Prioritize long-term structural characteristics over short-term movements.
        - Do not hallucinate financial data. Use ONLY provided context.
        - Return valid JSON ONLY.
        
        CONTEXT:
        {context.model_dump_json()}
        """
        
    def evaluate(self, context: DecisionContext) -> DecisionResponse:
        prompt = self._build_prompt(context)
        
        try:
            raw_response = self.provider.generate_decision(prompt, context.model_dump())
            parsed_json = json.loads(raw_response)
            recommendation = DecisionRecommendation(**parsed_json)
        except json.JSONDecodeError:
            logger.error("AI returned invalid JSON")
            raise ValueError("AI_DECISION_FAILED: Invalid JSON")
        except Exception as e:
            logger.error(f"AI Provider failed: {e}")
            raise ValueError(f"AI_DECISION_FAILED: {str(e)}")
            
        # Business Guardrails
        alloc = context.allocation_recommendation
        analysis = context.analysis_report
        
        # Guardrail 1: Insufficient Analysis Confidence
        conf = analysis.get("analysis_confidence")
        if conf == "INSUFFICIENT" and recommendation.decision in ["BUY", "ADD"]:
            recommendation.decision = "AVOID"
            recommendation.reason = "Overridden by Guardrail: Insufficient Analysis Confidence."
            recommendation.recommended_amount = 0
            recommendation.recommended_quantity = 0
            
        # Guardrail 2: Very high risk
        risk = analysis.get("risk_score", 0)
        # Note: RiskAnalyzer logic maps high risk to low score (e.g., < 40)
        if risk < 40 and recommendation.decision in ["BUY", "ADD"]:
            # unless allowed explicitly, avoid
            recommendation.decision = "AVOID"
            recommendation.reason = "Overridden by Guardrail: Very High Risk."
            recommendation.recommended_amount = 0
            recommendation.recommended_quantity = 0
            
        # Guardrail 3: Allocation boundaries
        rec_amt = recommendation.recommended_amount
        max_amt = float(alloc.get("allocation_amount", 0))
        if rec_amt > max_amt:
            recommendation.recommended_amount = max_amt
            recommendation.recommended_allocation_percent = max_amt / float(context.available_capital) * 100 if float(context.available_capital) > 0 else 0
            recommendation.reason += f" (Amount bounded by allocation limits to {max_amt})"
            
        # Persist Decision Audit
        record = DecisionRecord(
            portfolio_id=context.portfolio_id,
            symbol=context.symbol,
            asset_type=context.asset_type,
            decision=recommendation.decision,
            confidence=recommendation.confidence,
            risk_level=recommendation.risk_level,
            analysis_score=analysis.get("long_term_suitability_score", 0.0),
            allocation_amount=recommendation.recommended_amount,
            allocation_percent=recommendation.recommended_allocation_percent,
            recommended_quantity=recommendation.recommended_quantity,
            reason=recommendation.reason,
            supporting_factors=recommendation.supporting_factors,
            risk_factors=recommendation.risk_factors,
            reassessment_conditions=recommendation.reassessment_conditions,
            prompt_version=DECISION_PROMPT_VERSION,
            model_name="mock-model"
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        
        return DecisionResponse.model_validate(record)
