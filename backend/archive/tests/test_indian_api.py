import os
from unittest.mock import patch, MagicMock

import httpx
import pytest

from app.services.fundamentals.eodhd import FundamentalProviderStatus
from app.services.fundamentals.indian_api import IndianAPIFundamentalDataProvider

@pytest.fixture
def isolated_indian_api():
    """Provider without relying on actual environment variables."""
    return IndianAPIFundamentalDataProvider(api_key="valid_key")


def test_missing_api_key():
    provider = IndianAPIFundamentalDataProvider(api_key="")
    result = provider.get_fundamentals("HEROMOTOCO-EQ")
    assert result.status == FundamentalProviderStatus.UNAVAILABLE
    assert "INDIAN_API_KEY not set" in result.error_message


def test_invalid_placeholder_api_key():
    provider = IndianAPIFundamentalDataProvider(api_key="your_indian_api_key_here")
    result = provider.get_fundamentals("HEROMOTOCO-EQ")
    assert result.status == FundamentalProviderStatus.UNAVAILABLE
    assert "INDIAN_API_KEY not set" in result.error_message


@patch("app.services.fundamentals.indian_api.httpx.Client")
def test_successful_response(mock_client_class, isolated_indian_api):
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "isin": "INE158A01026",
        "name": "Hero MotoCorp Ltd",
        "revenue": 34000.5,
        "netProfit": 3000.2,
        "pe": 15.5
    }
    mock_client.get.return_value = mock_response
    
    result = isolated_indian_api.get_fundamentals("HEROMOTOCO-EQ", isin="INE158A01026")
    
    assert result.status == FundamentalProviderStatus.AVAILABLE
    assert result.identity_verified is True
    assert result.revenue == 34000.5
    assert result.net_profit == 3000.2
    assert result.pe_ratio == 15.5
    assert "revenue" in result.available_fields
    assert "revenue_growth" in result.unavailable_fields


@patch("app.services.fundamentals.indian_api.httpx.Client")
def test_company_identity_mismatch(mock_client_class, isolated_indian_api):
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "isin": "INE999Z99999",  # Different ISIN
        "name": "Some Other Co",
        "revenue": 100
    }
    mock_client.get.return_value = mock_response
    
    result = isolated_indian_api.get_fundamentals("HEROMOTOCO-EQ", isin="INE158A01026")
    
    assert result.status == FundamentalProviderStatus.UNAVAILABLE
    assert result.identity_verified is False
    assert "ISIN MISMATCH" in result.error_message


@pytest.mark.parametrize("status_code, expected_status", [
    (401, FundamentalProviderStatus.AUTH_ERROR),
    (403, FundamentalProviderStatus.FORBIDDEN),
    (404, FundamentalProviderStatus.NOT_FOUND),
    (429, FundamentalProviderStatus.RATE_LIMITED),
    (500, FundamentalProviderStatus.PROVIDER_ERROR),
])
@patch("app.services.fundamentals.indian_api.httpx.Client")
def test_http_errors(mock_client_class, isolated_indian_api, status_code, expected_status):
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_client.get.return_value = mock_response
    
    result = isolated_indian_api.get_fundamentals("HEROMOTOCO-EQ")
    
    assert result.status == expected_status


@patch("app.services.fundamentals.indian_api.httpx.Client")
def test_timeout(mock_client_class, isolated_indian_api):
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    
    mock_client.get.side_effect = httpx.TimeoutException("Timeout")
    
    result = isolated_indian_api.get_fundamentals("HEROMOTOCO-EQ")
    
    assert result.status == FundamentalProviderStatus.UNAVAILABLE
    assert result.http_status == -1


@patch("app.services.fundamentals.indian_api.httpx.Client")
def test_malformed_response(mock_client_class, isolated_indian_api):
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    # JSON decoding fails
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_client.get.return_value = mock_response
    
    result = isolated_indian_api.get_fundamentals("HEROMOTOCO-EQ")
    
    # Provider treats it as None raw data
    assert result.status == FundamentalProviderStatus.UNAVAILABLE
