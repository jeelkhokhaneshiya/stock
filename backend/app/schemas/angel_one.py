"""
Safe, normalised Angel One read-only response schemas.

Rules enforced here:
- NO jwt_token / feed_token / api_key / password / totp_secret fields.
- All monetary values are Decimal strings (JSON-safe).
- Optional fields default to None; callers must handle missing broker data gracefully.
"""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Account / Profile
# ---------------------------------------------------------------------------

class AngelOneAccountInfo(BaseModel):
    """Safe subset of Angel One getProfile response.

    Never includes api_key, password, TOTP, jwt_token, or feed_token.
    """

    client_id: str = Field(..., description="Client code (redacted tail for display)")
    name: str
    email: Optional[str] = None
    mobile: Optional[str] = None
    pan: Optional[str] = None          # included only if broker returns it; never log raw
    exchange_privileges: List[str] = Field(default_factory=list)
    product_privileges: List[str] = Field(default_factory=list)
    broker: str = "ANGEL_ONE"


# ---------------------------------------------------------------------------
# Funds / Margin
# ---------------------------------------------------------------------------

class AngelOneFundsResponse(BaseModel):
    """Normalised funds/margin view.  Never exposes raw broker payload."""

    broker: str = "ANGEL_ONE"
    available_cash: Decimal = Decimal("0.0")
    used_margin: Decimal = Decimal("0.0")
    net_cash: Decimal = Decimal("0.0")
    collateral: Decimal = Decimal("0.0")
    total_pnl: Optional[Decimal] = None
    currency: str = "INR"
    as_of: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Holdings  (delivery / long-term)
# ---------------------------------------------------------------------------

class AngelOneHoldingItem(BaseModel):
    symbol: str
    exchange: str
    isin: Optional[str] = None
    symbol_token: Optional[str] = None
    quantity: Decimal
    t1_quantity: Decimal = Decimal("0")   # unsettled shares
    average_price: Decimal
    last_price: Decimal = Decimal("0.0")
    market_value: Decimal = Decimal("0.0")
    pnl: Decimal = Decimal("0.0")
    pnl_percent: Decimal = Decimal("0.0")
    product: str = "DELIVERY"


class AngelOneHoldingsResponse(BaseModel):
    broker: str = "ANGEL_ONE"
    holdings: List[AngelOneHoldingItem] = Field(default_factory=list)
    count: int = 0
    as_of: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Positions  (intraday / overnight open)
# ---------------------------------------------------------------------------

class AngelOnePositionItem(BaseModel):
    symbol: str
    exchange: str
    symbol_token: Optional[str] = None
    product: str
    side: str                       # "BUY" | "SELL"
    quantity: Decimal
    average_price: Decimal
    last_price: Decimal = Decimal("0.0")
    pnl: Decimal = Decimal("0.0")
    pnl_percent: Decimal = Decimal("0.0")
    close_price: Decimal = Decimal("0.0")


class AngelOnePositionsResponse(BaseModel):
    broker: str = "ANGEL_ONE"
    positions: List[AngelOnePositionItem] = Field(default_factory=list)
    count: int = 0
    as_of: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Order Book  (read-only view)
# ---------------------------------------------------------------------------

class AngelOneOrderItem(BaseModel):
    broker_order_id: str
    symbol: str
    exchange: str
    side: str                   # "BUY" | "SELL"
    order_type: str             # "MARKET" | "LIMIT" | ...
    product: str
    quantity: Decimal
    price: Decimal
    trigger_price: Decimal = Decimal("0.0")
    status: str
    status_message: Optional[str] = None
    filled_quantity: Decimal = Decimal("0")
    remaining_quantity: Decimal = Decimal("0")
    average_fill_price: Decimal = Decimal("0.0")
    placed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AngelOneOrdersResponse(BaseModel):
    broker: str = "ANGEL_ONE"
    orders: List[AngelOneOrderItem] = Field(default_factory=list)
    count: int = 0
    as_of: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Generic safe error wrapper (never exposes secrets)
# ---------------------------------------------------------------------------

class BrokerDataError(BaseModel):
    provider: str = "angel_one"
    error_code: str
    message: str               # safe, non-sensitive description only
    live_trading_enabled: bool = False
