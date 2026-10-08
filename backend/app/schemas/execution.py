from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, List

class OrderState:
    SHADOW = "SHADOW"
    READY_FOR_CONFIRMATION = "READY_FOR_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    SUBMITTED = "SUBMITTED"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    EXECUTION_BLOCKED = "EXECUTION_BLOCKED"

class OrderIntent(BaseModel):
    intent_id: str = Field(default="", description="Unique identifier for the intent")
    symbol: str = Field(..., description="Trading symbol")
    symboltoken: str = Field(..., description="Angel One symbol token")
    exchange: str = Field(..., description="Exchange (e.g., NSE, BSE)")
    transaction_type: str = Field(..., description="BUY or SELL")
    product_type: str = Field(..., description="DELIVERY, INTRADAY, etc.")
    order_type: str = Field(..., description="MARKET or LIMIT")
    quantity: int = Field(..., description="Quantity to transact")
    price: float = Field(..., description="Price for limit order or 0 for market order")
    estimated_value: float = Field(..., description="Estimated total value of the transaction")
    decision_reason: str = Field(..., description="Reasoning from the decision engine")
    timestamp: datetime = Field(..., description="Time of intent generation")

class OrderPreview(BaseModel):
    preview_id: str
    intent_id: str
    symbol: str
    company_name: str
    exchange: str
    transaction_type: str
    product_type: str
    quantity: int
    current_ltp: float
    order_type: str
    limit_price: Optional[float]
    estimated_amount: float
    available_cash: float
    expected_remaining_cash: float
    current_holding_quantity: int
    expected_holding_quantity: int
    decision_reason: str
    fundamental_score: float
    technical_score: float
    valuation_score: float
    risk_score: float
    main_risks: List[str]
    data_timestamp: datetime
    data_freshness: str
    order_validity_expiry: datetime
    state: str = OrderState.READY_FOR_CONFIRMATION

class OrderConfirmation(BaseModel):
    confirmation_id: str
    preview_id: str
    user_id: str
    timestamp: datetime
    ip_address: Optional[str] = None

class BrokerResponse(BaseModel):
    broker_order_id: str
    symbol: str
    quantity: int
    transaction_type: str
    status: str
    rejection_reason: Optional[str] = None
    timestamp: datetime
    
class ExecutionResult(BaseModel):
    intent_id: str
    preview_id: Optional[str]
    confirmation_id: Optional[str]
    broker_order_id: Optional[str]
    status: str
    message: str
    timestamp: datetime

