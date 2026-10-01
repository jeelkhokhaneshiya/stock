from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from app.models.enums import ReconciliationStatus, ReconciliationSeverity

class CashReconciliation(BaseModel):
    broker_cash: Decimal
    internal_cash: Decimal
    cash_difference: Decimal

class HoldingsReconciliation(BaseModel):
    matched_count: int
    mismatch_count: int
    broker_only_count: int
    internal_only_count: int

class ReconciliationItemSchema(BaseModel):
    symbol: Optional[str] = None
    isin: Optional[str] = None
    exchange: Optional[str] = None
    asset_type: Optional[str] = None
    
    broker_quantity: Optional[Decimal] = None
    internal_quantity: Optional[Decimal] = None
    quantity_difference: Optional[Decimal] = None
    
    broker_average_price: Optional[Decimal] = None
    internal_average_price: Optional[Decimal] = None
    average_price_difference: Optional[Decimal] = None
    
    broker_market_value: Optional[Decimal] = None
    internal_market_value: Optional[Decimal] = None
    market_value_difference: Optional[Decimal] = None
    
    status: ReconciliationStatus
    severity: ReconciliationSeverity
    reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ReconciliationReport(BaseModel):
    reconciliation_id: Optional[int] = None
    portfolio_id: int
    broker: str
    status: ReconciliationStatus
    generated_at: datetime
    
    cash: CashReconciliation
    holdings: HoldingsReconciliation
    items: List[ReconciliationItemSchema]
    
    summary: str

    model_config = ConfigDict(from_attributes=True)
