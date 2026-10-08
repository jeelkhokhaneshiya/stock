from __future__ import annotations
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class FundamentalProviderStatus(str, Enum):
    AVAILABLE       = "AVAILABLE"
    UNAVAILABLE     = "UNAVAILABLE"
    AUTH_ERROR      = "AUTH_ERROR"
    FORBIDDEN       = "FORBIDDEN"
    NOT_FOUND       = "NOT_FOUND"
    RATE_LIMITED    = "RATE_LIMITED"
    PROVIDER_ERROR  = "PROVIDER_ERROR"
    IDENTITY_ERROR  = "IDENTITY_ERROR"
    STALE           = "STALE"
    SUBSCRIPTION_BLOCKED = "SUBSCRIPTION_BLOCKED"

@dataclass
class FundamentalResult:
    status:             FundamentalProviderStatus
    provider:           str = "UNKNOWN"
    http_status:        Optional[int] = None

    # Company identity
    isin:               Optional[str] = None
    symbol:             Optional[str] = None        # Angel One symbol e.g. HEROMOTORS-EQ
    exchange:           Optional[str] = None
    provider_ticker:    Optional[str] = None        # e.g. HEROMOTOCO.NSE
    company_name:       Optional[str] = None
    identity_verified:  bool = False

    # Financials
    revenue:                    Optional[float] = None
    revenue_growth:             Optional[float] = None
    operating_profit:           Optional[float] = None
    operating_profit_growth:    Optional[float] = None
    net_profit:                 Optional[float] = None
    profit_growth:              Optional[float] = None
    eps:                        Optional[float] = None
    eps_growth:                 Optional[float] = None

    # Quality
    roe:                Optional[float] = None
    roa:                Optional[float] = None
    roce:               Optional[float] = None
    debt_to_equity:     Optional[float] = None
    free_cash_flow:     Optional[float] = None

    # Valuation
    pe_ratio:           Optional[float] = None
    pb_ratio:           Optional[float] = None
    ev_to_ebitda:       Optional[float] = None
    book_value:         Optional[float] = None
    market_cap:         Optional[float] = None
    peg_ratio:          Optional[float] = None
    dividend_yield:     Optional[float] = None

    # Shareholding
    promoter_holding:      Optional[float] = None
    institutional_holding: Optional[float] = None
    public_holding:        Optional[float] = None

    # Metadata
    timestamp:          Optional[str] = None
    reporting_period:   Optional[str] = None
    error_message:      Optional[str] = None
    available_fields:   list = field(default_factory=list)
    unavailable_fields: list = field(default_factory=list)
    confidence:         float = 0.0

    # Backwards compatibility with previous versions
    @property
    def eodhd_ticker(self):
        return self.provider_ticker

    def calculate_confidence(self) -> None:
        if self.status != FundamentalProviderStatus.AVAILABLE:
            self.confidence = 0.0
            return
            
        if not self.identity_verified:
            self.confidence = 0.0
            return
            
        core_fields = [
            self.revenue, self.net_profit, self.roe, 
            self.pe_ratio, self.debt_to_equity
        ]
        
        present = sum(1 for f in core_fields if f is not None)
        self.confidence = float(present) / len(core_fields)

class FundamentalDataProvider:
    def get_fundamentals(self, symbol: str, exchange: str, isin: str = "") -> FundamentalResult:
        raise NotImplementedError

class FundamentalProviderRegistry:
    def __init__(self):
        self._providers: Dict[str, FundamentalDataProvider] = {}
        self._priority: List[str] = []

    def register(self, name: str, provider: FundamentalDataProvider, priority: int = 0):
        self._providers[name] = provider
        if name not in self._priority:
            self._priority.append(name)

    def set_priority(self, names: List[str]):
        """Set the priority order of providers. Names not in the list will be checked after."""
        ordered = [n for n in names if n in self._providers]
        remaining = [n for n in self._providers if n not in names]
        self._priority = ordered + remaining

    def get_fundamentals(self, symbol: str, exchange: str, isin: str = "") -> FundamentalResult:
        errors = []
        for name in self._priority:
            provider = self._providers[name]
            try:
                result = provider.get_fundamentals(symbol, exchange, isin)
                if result.status == FundamentalProviderStatus.AVAILABLE:
                    result.calculate_confidence()
                    if result.confidence > 0.2:
                        return result
                    else:
                        errors.append(f"{name}: Low confidence ({result.confidence})")
                else:
                    errors.append(f"{name}: {result.status.name}")
            except Exception as e:
                logger.error(f"Provider {name} raised an error: {str(e)}")
                errors.append(f"{name}: EXCEPTION")
        
        # If all fail, return unavailable
        return FundamentalResult(
            status=FundamentalProviderStatus.UNAVAILABLE,
            provider="REGISTRY",
            error_message="; ".join(errors)
        )
