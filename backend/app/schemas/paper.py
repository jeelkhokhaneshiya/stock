from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.models.enums import AssetType, OrderSide, OrderStatus

class PaperAccountCreate(BaseModel):
    portfolio_id: int
    initial_cash: float = 100000.0

class PaperAccountResponse(BaseModel):
    id: int
    portfolio_id: int
    initial_cash: float
    available_cash: float
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

class OrderRequest(BaseModel):
    client_order_id: str
    symbol: str
    instrument_type: AssetType
    quantity: float
    price: float

class OrderResponse(BaseModel):
    id: int
    client_order_id: str
    symbol: str
    instrument_type: AssetType
    side: OrderSide
    quantity: float
    requested_price: float
    executed_price: Optional[float]
    status: OrderStatus
    reject_reason: Optional[str]
    created_at: Optional[datetime]
    executed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

class HoldingResponse(BaseModel):
    id: int
    symbol: str
    instrument_type: AssetType
    quantity: float
    average_price: float

    model_config = ConfigDict(from_attributes=True)
