import pytest
from unittest.mock import MagicMock, patch
from app.services.portfolio.portfolio_manager import PortfolioManager
from app.services.brokers.angel_one.exceptions import AngelOneAuthenticationError, AngelOneNetworkError

@pytest.fixture
def mock_client():
    client = MagicMock()
    # auth is an object
    client.auth = MagicMock()
    return client

def test_disconnected_broker_returns_safe_response(mock_client):
    mock_client.auth.is_authenticated.return_value = False
    # When get_funds is called, we simulate a network timeout because authenticate is called internally
    mock_client.get_funds.side_effect = AngelOneNetworkError("Connection timed out")
    
    manager = PortfolioManager(client=mock_client)
    res = manager.get_full_portfolio_analysis()
    
    # Assert safe response structure
    assert res["status"] == "BROKER_DISCONNECTED"
    assert res["data_freshness"] == "UNAVAILABLE"
    assert res["portfolio_summary"]["total_portfolio_value"] == 0
    assert "reason" in res
    assert "timed out" in res["reason"].lower()
    
    # Assert NO fake data
    assert len(res["holdings_analysis"]) == 0
    assert len(res["buy_candidates"]) == 0
    
def test_authentication_failure_returns_safe_response(mock_client):
    mock_client.auth.is_authenticated.return_value = False
    mock_client.get_funds.side_effect = AngelOneAuthenticationError("Invalid TOTP")
    
    manager = PortfolioManager(client=mock_client)
    res = manager.get_full_portfolio_analysis()
    
    assert res["status"] == "BROKER_DISCONNECTED"
    assert "invalid totp" in res["reason"].lower()

@patch('app.services.portfolio.portfolio_manager.get_angel_one_data_service')
def test_broker_not_initialized_returns_safe_response(mock_get_service):
    # If client is None and get_angel_one_data_service returns None
    mock_get_service.return_value = None
    manager = PortfolioManager(client=None)
    res = manager.get_full_portfolio_analysis()
    
    assert res["status"] == "BROKER_DISCONNECTED"
    assert "not initialized" in res["reason"].lower()

def test_auth_storm_prevention():
    # Because AngelOneAuth is a singleton that manages its own locks in get_session,
    # the client relies on auth.is_authenticated(). If auth is valid, no authenticate() is called.
    client = MagicMock()
    client.auth.is_authenticated.return_value = True
    
    manager = PortfolioManager(client=client)
    
    # Force an exception downstream to stop execution early but prove auth was skipped
    client.get_funds.side_effect = AngelOneNetworkError("Failed to fetch funds")
    
    res = manager.get_full_portfolio_analysis()
    
    assert res["status"] == "BROKER_DISCONNECTED"
    # Authenticate must NOT be called if already authenticated
    client.authenticate.assert_not_called()
