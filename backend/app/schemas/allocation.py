from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from decimal import Decimal
from app.models.enums import AssetType

RiskProfile = Literal["CONSERVATIVE", "MODERATE", "AGGRESSIVE"]
InvestmentHorizon = Literal["SHORT_TERM", "MEDIUM_TERM", "LONG_TERM"]
AllocationAction = Literal["NEW_POSITION", "ADD", "HOLD", "REDUCE", "EXIT", "REJECTED"]

class AllocationCandidate(BaseModel):
    symbol: str
    asset_type: AssetType = AssetType.STOCK

class AllocationPreviewRequest(BaseModel):
    capital: Decimal = Field(..., ge=0)
    risk_profile: RiskProfile = "MODERATE"
    investment_horizon: InvestmentHorizon = "LONG_TERM"
    candidates: List[AllocationCandidate]

class HoldingData(BaseModel):
    symbol: str
    asset_type: AssetType
    quantity: Decimal
    average_cost: Decimal

class PortfolioData(BaseModel):
    id: str
    cash_balance: Decimal
    currency: str = "INR"
    holdings: List[HoldingData] = []

class PortfolioHoldingInfo(BaseModel):
    symbol: str
    asset_type: AssetType
    quantity: Decimal
    average_cost: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_percent: Decimal
    sector: Optional[str] = None
    currency: str = "INR"

class PortfolioAnalysisReport(BaseModel):
    portfolio_id: str
    total_portfolio_value: Decimal
    invested_value: Decimal
    available_cash: Decimal
    cash_percentage: Decimal
    number_of_holdings: int
    holdings: List[PortfolioHoldingInfo]
    largest_position_symbol: Optional[str]
    smallest_position_symbol: Optional[str]

class AllocationRecommendation(BaseModel):
    symbol: str
    asset_type: AssetType
    action: AllocationAction
    allocation_percent: Decimal
    allocation_amount: Decimal
    current_price: Decimal
    recommended_quantity: Decimal
    analysis_score: float
    risk_score: float
    confidence: str
    reason: str

class PortfolioAllocationReport(BaseModel):
    portfolio_id: str
    available_capital: Decimal
    cash_reserve: Decimal
    capital_available_for_allocation: Decimal
    recommendations: List[AllocationRecommendation]
    unallocated_cash: Decimal
    portfolio_risk: str
    diversification_status: str
    warnings: List[str]
