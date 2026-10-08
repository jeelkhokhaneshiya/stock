import pytest
from app.services.fundamentals.base import (
    FundamentalProviderRegistry, 
    FundamentalDataProvider, 
    FundamentalResult,
    FundamentalProviderStatus
)

class MockProvider(FundamentalDataProvider):
    def __init__(self, result: FundamentalResult):
        self.result = result
        
    def get_fundamentals(self, symbol: str, exchange: str, isin: str = "") -> FundamentalResult:
        return self.result

def test_registry_failover():
    # Primary fails (AUTH_ERROR), secondary succeeds
    primary = MockProvider(FundamentalResult(status=FundamentalProviderStatus.AUTH_ERROR, provider="MOCK1"))
    secondary = MockProvider(
        FundamentalResult(
            status=FundamentalProviderStatus.AVAILABLE, 
            provider="MOCK2", 
            identity_verified=True, 
            revenue=100, 
            net_profit=10, 
            roe=0.15,
            pe_ratio=15.0,
            debt_to_equity=0.5
        )
    )
    
    registry = FundamentalProviderRegistry()
    registry.register("primary", primary)
    registry.register("secondary", secondary)
    registry.set_priority(["primary", "secondary"])
    
    result = registry.get_fundamentals("TEST", "NSE")
    assert result.status == FundamentalProviderStatus.AVAILABLE
    assert result.provider == "MOCK2"
    assert result.confidence == 1.0

def test_registry_all_fail():
    primary = MockProvider(FundamentalResult(status=FundamentalProviderStatus.AUTH_ERROR, provider="MOCK1"))
    secondary = MockProvider(FundamentalResult(status=FundamentalProviderStatus.NOT_FOUND, provider="MOCK2"))
    
    registry = FundamentalProviderRegistry()
    registry.register("primary", primary)
    registry.register("secondary", secondary)
    
    result = registry.get_fundamentals("TEST", "NSE")
    assert result.status == FundamentalProviderStatus.UNAVAILABLE
    assert result.provider == "REGISTRY"
    assert "MOCK1" not in result.error_message # error message contains provider names (primary, secondary)
    assert "primary: AUTH_ERROR" in result.error_message
    assert "secondary: NOT_FOUND" in result.error_message

def test_registry_low_confidence_skips():
    primary = MockProvider(
        FundamentalResult(
            status=FundamentalProviderStatus.AVAILABLE, 
            provider="MOCK1", 
            identity_verified=True, 
            revenue=None, 
            net_profit=None, 
            roe=None,
            pe_ratio=None,
            debt_to_equity=None
        )
    )
    secondary = MockProvider(
        FundamentalResult(
            status=FundamentalProviderStatus.AVAILABLE, 
            provider="MOCK2", 
            identity_verified=True, 
            revenue=100, 
            net_profit=10, 
            roe=0.15,
            pe_ratio=15.0,
            debt_to_equity=0.5
        )
    )
    
    registry = FundamentalProviderRegistry()
    registry.register("primary", primary)
    registry.register("secondary", secondary)
    
    result = registry.get_fundamentals("TEST", "NSE")
    assert result.status == FundamentalProviderStatus.AVAILABLE
    assert result.provider == "MOCK2"

def test_fundamental_confidence_degradation():
    # All core fields missing
    result1 = FundamentalResult(status=FundamentalProviderStatus.AVAILABLE, provider="MOCK", identity_verified=True)
    result1.calculate_confidence()
    assert result1.confidence == 0.0
    
    # Half core fields present
    result2 = FundamentalResult(status=FundamentalProviderStatus.AVAILABLE, provider="MOCK", identity_verified=True, revenue=100, net_profit=10)
    result2.calculate_confidence()
    assert result2.confidence == 2/5
    
    # Missing identity
    result3 = FundamentalResult(status=FundamentalProviderStatus.AVAILABLE, provider="MOCK", identity_verified=False, revenue=100, net_profit=10)
    result3.calculate_confidence()
    assert result3.confidence == 0.0

    # Not available
    result4 = FundamentalResult(status=FundamentalProviderStatus.STALE, provider="MOCK", identity_verified=True, revenue=100, net_profit=10)
    result4.calculate_confidence()
    assert result4.confidence == 0.0
