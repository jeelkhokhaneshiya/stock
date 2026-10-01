from pydantic import BaseModel, Field, validator, ConfigDict
from typing import List, Literal, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.models.enums import AssetType

DecisionType = Literal["BUY", "HOLD", "ADD", "REDUCE", "SELL", "AVOID"]
ConfidenceCategory = Literal["LOW", "MEDIUM", "HIGH"]

class DecisionRecommendation(BaseModel):
    decision: DecisionType
    confidence: float = Field(..., ge=0.0, le=1.0)
    risk_level: str
    recommended_allocation_percent: Decimal = Field(..., ge=0, le=100)
    recommended_amount: Decimal = Field(..., ge=0)
    recommended_quantity: Decimal = Field(..., ge=0)
    holding_period: str = "LONG_TERM"
    reason: str
    supporting_factors: List[str] = []
    risk_factors: List[str] = []
    reassessment_conditions: List[str] = []
    
class DecisionContext(BaseModel):
    symbol: str
    asset_type: AssetType
    portfolio_id: str
    analysis_report: Dict[str, Any]
    allocation_recommendation: Dict[str, Any]
    current_holding: Optional[Dict[str, Any]] = None
    risk_profile: str
    investment_horizon: str
    available_capital: Decimal
    warnings: List[str] = []

class DecisionResponse(BaseModel):
    id: int
    portfolio_id: str
    symbol: str
    asset_type: AssetType
    decision: DecisionType
    confidence: float
    risk_level: str
    analysis_score: float
    allocation_amount: Decimal
    allocation_percent: Decimal
    recommended_quantity: Decimal
    reason: str
    supporting_factors: List[str]
    risk_factors: List[str]
    reassessment_conditions: List[str]
    prompt_version: str
    model_name: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
