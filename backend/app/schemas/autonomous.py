from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any
from datetime import datetime
from app.models.enums import CycleStatus, ExecutionIntent, DecisionAction, ExecutionStatus, AssetType, OrderSide

class AutonomousCycleResult(BaseModel):
    cycle_id: int
    portfolio_id: str
    status: CycleStatus
    market_status: str
    candidate_count: int = 0
    analysis_count: int = 0
    decision_count: int = 0
    approved_count: int = 0
    modified_count: int = 0
    rejected_count: int = 0
    executed_count: int = 0
    failed_count: int = 0
    total_buy_amount: float = 0.0
    total_sell_amount: float = 0.0
    errors: List[str] = []
    warnings: List[str] = []
    execution_ids: List[int] = []

class AutonomousCycleResponse(AutonomousCycleResult):
    started_at: datetime
    completed_at: Optional[datetime] = None
    summary: Optional[Any] = None
    model_config = ConfigDict(from_attributes=True)

class AutonomousExecutionResponse(BaseModel):
    id: int
    portfolio_id: str
    decision_id: Optional[int] = None
    risk_approval_id: Optional[int] = None
    symbol: str
    asset_type: AssetType
    side: OrderSide
    execution_intent: ExecutionIntent
    requested_quantity: float
    approved_quantity: float
    executed_quantity: float
    requested_amount: float
    approved_amount: float
    executed_amount: float
    price: Optional[float] = None
    status: ExecutionStatus
    broker_order_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class AutonomousStatusResponse(BaseModel):
    portfolio_id: str
    autonomous_mode: bool
    broker_mode: str
    market_status: str
    last_cycle_id: Optional[int] = None
    last_cycle_status: Optional[CycleStatus] = None
    last_cycle_at: Optional[datetime] = None
    current_cash: float
    portfolio_value: float
    holding_count: int
    last_error: Optional[str] = None
