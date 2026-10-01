from typing import Dict, Any
import json
from app.services.ai.provider import AIProvider

class MockAIProvider(AIProvider):
    def __init__(self, mode: str = "VALID_BUY"):
        self.mode = mode

    def generate_decision(self, prompt: str, context: Dict[str, Any]) -> str:
        if self.mode == "TIMEOUT":
            raise TimeoutError("AI Provider Timeout")
        if self.mode == "PROVIDER_FAILURE":
            raise ValueError("Provider Failure")
        if self.mode == "INVALID_JSON":
            return "{ invalid json"
        
        # Valid modes
        decision = "BUY"
        if self.mode == "VALID_SELL": decision = "SELL"
        if self.mode == "VALID_HOLD": decision = "HOLD"
        if self.mode == "VALID_ADD": decision = "ADD"
        if self.mode == "VALID_REDUCE": decision = "REDUCE"
        if self.mode == "VALID_AVOID": decision = "AVOID"
        if self.mode == "INVALID_DECISION": decision = "SHORT"
        
        if self.mode == "HALLUCINATED_DATA":
            return json.dumps({
                "decision": "BUY",
                "confidence": 0.9,
                "risk_level": "MODERATE",
                "recommended_allocation_percent": 150, # Hallucinated > 100
                "recommended_amount": 999999, # Hallucinated
                "recommended_quantity": 9999, # Hallucinated
                "holding_period": "LONG_TERM",
                "reason": "Because I predict profit",
                "supporting_factors": [],
                "risk_factors": [],
                "reassessment_conditions": []
            })
            
        alloc_percent = context.get("allocation_recommendation", {}).get("allocation_percent", 10)
        alloc_amt = context.get("allocation_recommendation", {}).get("allocation_amount", 1000)
        qty = context.get("allocation_recommendation", {}).get("recommended_quantity", 10)
        
        # Default mock response
        resp = {
            "decision": decision,
            "confidence": 0.85,
            "risk_level": "MODERATE",
            "recommended_allocation_percent": float(alloc_percent),
            "recommended_amount": float(alloc_amt),
            "recommended_quantity": float(qty),
            "holding_period": "LONG_TERM",
            "reason": f"Decision {decision} generated for tests",
            "supporting_factors": ["Good score"],
            "risk_factors": ["Market risk"],
            "reassessment_conditions": ["Price drops 10%"]
        }
        
        if self.mode == "MISSING_FIELDS":
            del resp["confidence"]
            
        return json.dumps(resp)
