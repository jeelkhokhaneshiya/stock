from pydantic import BaseModel, Field, ConfigDict
from typing import List, Literal, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.models.enums import AssetType
from app.schemas.decision import DecisionRecommendation

ExecutionIntent = Literal["DELIVERY_LONG_TERM"]
RiskCheckStatus = Literal["PASSED", "FAILED", "WARNING", "NOT_VERIFIED"]
ApprovalStatus = Literal["APPROVED", "REJECTED", "MODIFIED", "NO_EXECUTION_REQUIRED"]

class RiskCheck(BaseModel):
    check: str
    status: RiskCheckStatus
    message: str

class RiskApprovalRequest(BaseModel):
    decision: DecisionRecommendation
    portfolio_id: str
    symbol: str
    asset_type: AssetType
    current_price: Decimal
    available_cash: Decimal
    current_quantity: Decimal = Decimal(0)
    current_exposure: Decimal = Decimal(0)
    portfolio_total_value: Decimal = Decimal(0)
    risk_profile: str
    analysis_confidence: str
    data_freshness_minutes: int = 0
    sector: Optional[str] = None
    sector_exposure: Decimal = Decimal(0)

class RiskApprovalResult(BaseModel):
    id: Optional[int] = None
    status: ApprovalStatus
    decision: str
    execution_intent: Optional[ExecutionIntent] = None
    requested_amount: Decimal
    approved_amount: Decimal
    requested_quantity: Decimal
    approved_quantity: Decimal
    checks: List[RiskCheck] = []
    warnings: List[str] = []
    rejection_reasons: List[str] = []
    modifications: List[str] = []
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class ExecutionRequest(BaseModel):
    symbol: str
    asset_type: AssetType
    side: Literal["BUY", "SELL"]
    quantity: Decimal
    execution_intent: ExecutionIntent
    order_type: Literal["MARKET", "LIMIT"]
    limit_price: Optional[Decimal] = None
    portfolio_id: str
