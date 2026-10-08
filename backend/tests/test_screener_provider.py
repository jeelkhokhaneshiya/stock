import pytest
from app.services.fundamentals.screener import ScreenerFundamentalDataProvider
from app.services.fundamentals.base import FundamentalProviderStatus

def test_screener_tcs():
    provider = ScreenerFundamentalDataProvider()
    result = provider.get_fundamentals("TCS-EQ", "NSE")
    
    assert result.status == FundamentalProviderStatus.AVAILABLE
    assert result.provider == "SCREENER"
    assert result.company_name is not None
    
    assert result.revenue is not None
    assert result.net_profit is not None
    assert result.eps is not None
    assert result.pe_ratio is not None
    assert result.roe is not None
    assert result.roce is not None
    assert result.book_value is not None
    assert result.promoter_holding is not None
    
    # Optional ones just ensure they are floats or None
    if result.free_cash_flow is not None:
        assert isinstance(result.free_cash_flow, float)
    if result.debt_to_equity is not None:
        assert isinstance(result.debt_to_equity, float)

def test_screener_heromoto():
    provider = ScreenerFundamentalDataProvider()
    result = provider.get_fundamentals("HEROMOTOCO", "NSE")
    
    assert result.status == FundamentalProviderStatus.AVAILABLE
    assert result.provider == "SCREENER"
    assert result.company_name is not None
    assert result.revenue is not None
    assert result.net_profit is not None
