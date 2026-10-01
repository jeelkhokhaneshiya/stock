from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from datetime import datetime
from app.core.config import settings

class MarketDataResponse(BaseModel):
    data_source: str
    timestamp: datetime
    is_stale: bool = False

class MarketQuote(MarketDataResponse):
    symbol: str
    exchange: str
    price: float = Field(..., gt=0)
    open: Optional[float] = Field(None, gt=0)
    high: Optional[float] = Field(None, gt=0)
    low: Optional[float] = Field(None, gt=0)
    previous_close: Optional[float] = Field(None, gt=0)
    volume: Optional[int] = Field(None, ge=0)
    currency: str

    @model_validator(mode='after')
    def validate_high_low(self) -> 'MarketQuote':
        if self.high is not None and self.low is not None:
            if self.high < self.low:
                raise ValueError("High cannot be less than low")
        return self

class HistoricalBar(BaseModel):
    symbol: str
    exchange: str
    timestamp: datetime
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: int = Field(..., ge=0)
    adjusted_close: Optional[float] = Field(None, gt=0)
    data_source: str

    @model_validator(mode='after')
    def validate_high_low(self) -> 'HistoricalBar':
        if self.high < self.low:
            raise ValueError("High cannot be less than low")
        return self

class HistoricalData(MarketDataResponse):
    bars: List[HistoricalBar]

class CompanyInfo(MarketDataResponse):
    symbol: str
    exchange: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    currency: Optional[str] = None
    market_cap: Optional[float] = Field(None, ge=0)

class FundamentalData(MarketDataResponse):
    symbol: str
    exchange: str
    revenue: Optional[float] = None
    revenue_growth: Optional[float] = None
    net_income: Optional[float] = None
    profit_growth: Optional[float] = None
    eps: Optional[float] = None
    roe: Optional[float] = None
    roce: Optional[float] = None
    debt_to_equity: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    free_cash_flow: Optional[float] = None

class ETFInfo(MarketDataResponse):
    symbol: str
    exchange: str
    name: str
    expense_ratio: Optional[float] = Field(None, ge=0)
    aum: Optional[float] = Field(None, ge=0)
    tracking_index: Optional[str] = None
    volume: Optional[int] = Field(None, ge=0)
    price: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = None

class MutualFundInfo(MarketDataResponse):
    identifier: str
    name: str
    category: Optional[str] = None
    nav: Optional[float] = Field(None, gt=0)
    nav_date: Optional[datetime] = None
    expense_ratio: Optional[float] = Field(None, ge=0)
    aum: Optional[float] = Field(None, ge=0)
    risk_category: Optional[str] = None
