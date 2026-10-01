from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from decimal import Decimal

class BrokerHolding(BaseModel):
    broker: str
    symbol: str
    exchange: str
    isin: Optional[str] = None
    symbol_token: Optional[str] = None
    quantity: Decimal
    average_price: Decimal
    last_price: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    profit_loss: Optional[Decimal] = None
    profit_loss_percent: Optional[Decimal] = None
    product: str
    t1_quantity: Optional[Decimal] = None

class BrokerBalance(BaseModel):
    available_cash: Decimal
    used_cash: Decimal
    total_cash: Decimal
    currency: str = "INR"
    broker: str

class BrokerOrder(BaseModel):
    broker_order_id: str
    symbol: str
    exchange: str
    side: str
    quantity: Decimal
    price: Decimal
    status: str
    product: str
    order_type: str
    created_at: datetime
    updated_at: Optional[datetime] = None

class BrokerHealthStatus(BaseModel):
    provider: str
    authenticated: bool
    reachable: bool
    last_successful_sync: Optional[datetime] = None
    last_error: Optional[str] = None
    mode: str = "PAPER"

from app.models.enums import OrderSide, ExecutionIntent, BrokerOrderStatus

class BrokerOrderRequest(BaseModel):
    client_order_id: str
    symbol: str
    isin: Optional[str] = None
    exchange: str
    side: OrderSide
    quantity: Decimal
    order_type: str
    price: Optional[Decimal] = None
    product: str
    execution_intent: ExecutionIntent
    portfolio_id: int

class BrokerOrderResponse(BaseModel):
    broker_order_id: str
    client_order_id: str
    status: BrokerOrderStatus
    executed_quantity: Decimal
    remaining_quantity: Decimal
    average_fill_price: Optional[Decimal] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None

class BrokerSnapshot(BaseModel):
    cash: BrokerBalance
    holdings: List[BrokerHolding]
    positions: List[dict] = []  # Can be expanded later if needed
    orders: List[BrokerOrder]
    timestamp: datetime
