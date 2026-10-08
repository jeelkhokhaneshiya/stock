import pytest
import httpx
from datetime import datetime
from app.services.fundamentals.fmp import FMPFundamentalDataProvider
from app.services.fundamentals.base import FundamentalProviderStatus, FundamentalResult

@pytest.fixture
def fmp_provider():
    return FMPFundamentalDataProvider(api_key="dummy_key", timeout=1.0)

def test_fmp_missing_api_key():
    provider = FMPFundamentalDataProvider(api_key=None)
    provider._api_key = None
    result = provider.get_fundamentals("HEROMOTOCO-EQ", "NSE", "INE158A01026")
    assert result.status == FundamentalProviderStatus.AUTH_ERROR
    assert result.error_message == "Missing API Key"

def test_fmp_timeout(fmp_provider, monkeypatch):
    def mock_get(*args, **kwargs):
        raise httpx.TimeoutException("Timeout")
    
    monkeypatch.setattr(httpx.Client, "get", mock_get)
    result = fmp_provider.get_fundamentals("HEROMOTOCO-EQ", "NSE", "INE158A01026")
    assert result.status == FundamentalProviderStatus.PROVIDER_ERROR

def test_fmp_http_errors(fmp_provider, monkeypatch):
    class MockResponse:
        def __init__(self, status_code, json_data=None):
            self.status_code = status_code
            self._json_data = json_data or {}
        def json(self):
            return self._json_data

    monkeypatch.setattr(httpx.Client, "get", lambda *args, **kwargs: MockResponse(401))
    assert fmp_provider.get_fundamentals("TEST", "NSE", "ISIN1").status == FundamentalProviderStatus.AUTH_ERROR

    monkeypatch.setattr(httpx.Client, "get", lambda *args, **kwargs: MockResponse(403))
    assert fmp_provider.get_fundamentals("TEST", "NSE", "ISIN1").status == FundamentalProviderStatus.AUTH_ERROR

    monkeypatch.setattr(httpx.Client, "get", lambda *args, **kwargs: MockResponse(429))
    assert fmp_provider.get_fundamentals("TEST", "NSE", "ISIN1").status == FundamentalProviderStatus.RATE_LIMITED

    monkeypatch.setattr(httpx.Client, "get", lambda *args, **kwargs: MockResponse(500))
    assert fmp_provider.get_fundamentals("TEST", "NSE", "ISIN1").status == FundamentalProviderStatus.PROVIDER_ERROR

def test_fmp_malformed_json(fmp_provider, monkeypatch):
    class MockResponse:
        status_code = 200
        def json(self):
            raise ValueError("Malformed JSON")
            
    monkeypatch.setattr(httpx.Client, "get", lambda *args, **kwargs: MockResponse())
    result = fmp_provider.get_fundamentals("TEST", "NSE", "ISIN1")
    assert result.status == FundamentalProviderStatus.PROVIDER_ERROR

def test_fmp_identity_mismatch(fmp_provider, monkeypatch):
    class MockResponse:
        status_code = 200
        def json(self):
            return [] 
            
    monkeypatch.setattr(httpx.Client, "get", lambda *args, **kwargs: MockResponse())
    result = fmp_provider.get_fundamentals("TEST", "NSE", "ISIN1")
    assert result.status == FundamentalProviderStatus.NOT_FOUND

def test_fmp_success_company_specific(fmp_provider, monkeypatch):
    def mock_get(self, url, params=None, **kwargs):
        class MockResponse:
            status_code = 200
            def __init__(self, data):
                self._data = data
            def json(self):
                return self._data
                
        if "search" in url:
            return MockResponse([{"symbol": "HEROMOTOCO.NS", "name": "Hero MotoCorp"}])
        if "income-statement" in url:
            return MockResponse([
                {"date": "2023-03-31", "revenue": 1000, "netIncome": 100, "eps": 10.5},
                {"date": "2022-03-31", "revenue": 800, "netIncome": 80, "eps": 8.0}
            ])
        if "balance-sheet-statement" in url:
            return MockResponse([{"totalAssets": 5000, "totalDebt": 200}])
        if "cash-flow-statement" in url:
            return MockResponse([{"freeCashFlow": 150}])
        if "key-metrics" in url:
            return MockResponse([{"peRatio": 15.5, "roe": 0.18, "debtToEquity": 0.5}])
            
        return MockResponse([])

    monkeypatch.setattr(httpx.Client, "get", mock_get)
    result = fmp_provider.get_fundamentals("HEROMOTOCO-EQ", "NSE", "INE158A01026")
    
    assert result.status == FundamentalProviderStatus.AVAILABLE
    assert result.symbol == "HEROMOTOCO-EQ"
    assert result.eps == 10.5
    assert result.pe_ratio == 15.5
    assert result.roe == 0.18
    assert result.free_cash_flow == 150
    assert result.revenue_growth == 0.25
    assert result.profit_growth == 0.25
    assert result.timestamp is not None
    assert result.identity_verified is True

def test_fmp_explicit_api_error_message(fmp_provider, monkeypatch):
    class MockResponse:
        status_code = 200
        def json(self):
            return {"Error Message": "Invalid API KEY"}
            
    monkeypatch.setattr(httpx.Client, "get", lambda *args, **kwargs: MockResponse())
    result = fmp_provider.get_fundamentals("TEST", "NSE", "ISIN1")
    assert result.status == FundamentalProviderStatus.AUTH_ERROR
