"""
test_angel_one_read_only.py
===========================
Tests for the Phase 9.2 Angel One read-only account data integration.

Covers:
- AngelOneDataService unit tests (success, auth failure, network failure,
  empty holdings, empty positions, malformed responses)
- API endpoint integration tests (/account, /funds, /holdings, /positions, /orders)
  - Authenticated requests
  - Unauthenticated requests (401)
  - Angel One success (mocked)
  - Angel One failure (mocked)
  - Empty holdings / positions
- Safety guard: confirms no live execution can be triggered
- Confirms ENABLE_LIVE_TRADING=False throughout

IMPORTANT: No real orders are placed.  All Angel One network calls are mocked.
"""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock
from fastapi.testclient import TestClient

from app.services.brokers.angel_one.auth import AngelOneAuth
from app.services.brokers.angel_one.client import AngelOneClient
from app.services.brokers.angel_one.data_service import AngelOneDataService
from app.services.brokers.angel_one.exceptions import (
    AngelOneAuthenticationError,
    AngelOneNetworkError,
    AngelOneRateLimitError,
    AngelOneInvalidResponseError,
)
from app.schemas.angel_one import (
    AngelOneAccountInfo,
    AngelOneFundsResponse,
    AngelOneHoldingsResponse,
    AngelOnePositionsResponse,
    AngelOneOrdersResponse,
)


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def mock_auth():
    auth = AngelOneAuth("FAKE_KEY", "FAKE_CLIENT", "FAKE_PASS", "FAKE_TOTP")
    auth.set_tokens("FAKE_JWT", "FAKE_REFRESH", "FAKE_FEED")
    return auth


@pytest.fixture
def mock_client(mock_auth):
    client = AngelOneClient(mock_auth)
    client.authenticate = MagicMock(return_value=True)
    return client


@pytest.fixture
def data_svc(mock_client):
    return AngelOneDataService(mock_client)


# ---------------------------------------------------------------------------
# Sample raw broker payloads  (representative — not real data)
# ---------------------------------------------------------------------------

SAMPLE_PROFILE = {
    "clientcode": "TESTCLIENT",
    "name": "Test User",
    "email": "test@example.com",
    "mobileno": "9999999999",
    "pan": "ABCDE1234F",
    "exchEnabled": "NSE|BSE|MCX",
    "products": "DELIVERY|INTRADAY",
}

SAMPLE_RMS = {
    "availablecash": "50000.00",
    "utilisedmargin": "10000.00",
    "netcashaval": "40000.00",
    "collateral": "5000.00",
    "unrealisedpnl": "2500.00",
}

SAMPLE_HOLDINGS = [
    {
        "tradingsymbol": "TCS-EQ",
        "exchange": "NSE",
        "isin": "INE467B01029",
        "symboltoken": "11536",
        "quantity": "10",
        "t1quantity": "0",
        "averageprice": "3500.00",
        "ltp": "3750.00",
        "marketvalue": "37500.00",
        "pnlpercentage": "7.14",
        "pnl": "2500.00",
        "product": "DELIVERY",
    },
    {
        "tradingsymbol": "INFY-EQ",
        "exchange": "NSE",
        "isin": "INE009A01021",
        "symboltoken": "1594",
        "quantity": "5",
        "t1quantity": "0",
        "averageprice": "1400.00",
        "ltp": "1500.00",
        "marketvalue": "7500.00",
        "pnlpercentage": "7.14",
        "pnl": "500.00",
        "product": "DELIVERY",
    },
]

SAMPLE_POSITIONS = [
    {
        "tradingsymbol": "NIFTY23OCTFUT",
        "exchange": "NFO",
        "symboltoken": "12345",
        "producttype": "CARRYFORWARD",
        "netqty": "1",
        "averageprice": "19000.00",
        "ltp": "19250.00",
        "close": "18900.00",
        "pnl": "250.00",
    }
]

SAMPLE_ORDERS = [
    {
        "orderid": "230101000000001",
        "tradingsymbol": "TCS-EQ",
        "exchange": "NSE",
        "transactiontype": "BUY",
        "ordertype": "LIMIT",
        "producttype": "DELIVERY",
        "quantity": "5",
        "price": "3600.00",
        "triggerprice": "0.00",
        "status": "complete",
        "text": "Order complete",
        "filledshares": "5",
        "unfilledshares": "0",
        "averageprice": "3590.00",
        "ordertime": "01-Jan-2023 10:15:00",
        "updatetime": "01-Jan-2023 10:16:00",
    }
]


# ===========================================================================
# Unit tests: AngelOneDataService
# ===========================================================================

class TestAngelOneDataServiceAccount:
    def test_get_account_success(self, data_svc, mock_client):
        mock_client.get_profile = MagicMock(return_value=SAMPLE_PROFILE)
        result = data_svc.get_account_info()

        assert isinstance(result, AngelOneAccountInfo)
        assert result.client_id == "TESTCLIENT"
        assert result.name == "Test User"
        assert result.email == "test@example.com"
        assert result.broker == "ANGEL_ONE"
        # Secrets must NOT be present on the schema at all
        assert not hasattr(result, "jwt_token")
        assert not hasattr(result, "api_key")
        assert not hasattr(result, "password")
        assert not hasattr(result, "totp_secret")
        assert not hasattr(result, "feed_token")

    def test_get_account_empty_response(self, data_svc, mock_client):
        mock_client.get_profile = MagicMock(return_value={})
        result = data_svc.get_account_info()
        assert result.client_id == "UNKNOWN"
        assert result.name == ""

    def test_get_account_auth_failure(self, data_svc, mock_client):
        mock_client.get_profile = MagicMock(side_effect=AngelOneAuthenticationError("expired"))
        with pytest.raises(AngelOneAuthenticationError):
            data_svc.get_account_info()

    def test_get_account_network_failure(self, data_svc, mock_client):
        mock_client.get_profile = MagicMock(side_effect=AngelOneNetworkError("timeout"))
        with pytest.raises(AngelOneNetworkError):
            data_svc.get_account_info()


class TestAngelOneDataServiceFunds:
    def test_get_funds_success(self, data_svc, mock_client):
        mock_client.get_rms = MagicMock(return_value=SAMPLE_RMS)
        result = data_svc.get_funds()

        assert isinstance(result, AngelOneFundsResponse)
        assert result.available_cash == Decimal("50000.00")
        assert result.used_margin == Decimal("10000.00")
        assert result.net_cash == Decimal("40000.00")
        assert result.collateral == Decimal("5000.00")
        assert result.currency == "INR"
        assert result.broker == "ANGEL_ONE"

    def test_get_funds_empty(self, data_svc, mock_client):
        mock_client.get_rms = MagicMock(return_value={})
        result = data_svc.get_funds()
        assert result.available_cash == Decimal("0.0")
        assert result.used_margin == Decimal("0.0")

    def test_get_funds_auth_failure(self, data_svc, mock_client):
        mock_client.get_rms = MagicMock(side_effect=AngelOneAuthenticationError("expired"))
        with pytest.raises(AngelOneAuthenticationError):
            data_svc.get_funds()


class TestAngelOneDataServiceHoldings:
    def test_get_holdings_success(self, data_svc, mock_client):
        mock_client.get_holdings = MagicMock(return_value=SAMPLE_HOLDINGS)
        result = data_svc.get_holdings()

        assert isinstance(result, AngelOneHoldingsResponse)
        assert result.count == 2
        assert len(result.holdings) == 2
        assert result.holdings[0].symbol == "TCS-EQ"
        assert result.holdings[0].quantity == Decimal("10")
        assert result.holdings[0].average_price == Decimal("3500.00")
        assert result.holdings[0].product == "DELIVERY"

    def test_get_holdings_empty(self, data_svc, mock_client):
        """Empty holdings list is valid — not an error."""
        mock_client.get_holdings = MagicMock(return_value=[])
        result = data_svc.get_holdings()
        assert result.count == 0
        assert result.holdings == []

    def test_get_holdings_none(self, data_svc, mock_client):
        mock_client.get_holdings = MagicMock(return_value=None)
        result = data_svc.get_holdings()
        assert result.count == 0

    def test_get_holdings_malformed_record_skipped(self, data_svc, mock_client):
        """Malformed records should be skipped gracefully, valid ones kept."""
        mixed = [
            None,
            "not a dict",
            SAMPLE_HOLDINGS[0],
        ]
        mock_client.get_holdings = MagicMock(return_value=mixed)
        result = data_svc.get_holdings()
        assert result.count == 1
        assert result.holdings[0].symbol == "TCS-EQ"

    def test_get_holdings_auth_failure(self, data_svc, mock_client):
        mock_client.get_holdings = MagicMock(side_effect=AngelOneAuthenticationError("expired"))
        with pytest.raises(AngelOneAuthenticationError):
            data_svc.get_holdings()

    def test_get_holdings_network_failure(self, data_svc, mock_client):
        mock_client.get_holdings = MagicMock(side_effect=AngelOneNetworkError("timeout"))
        with pytest.raises(AngelOneNetworkError):
            data_svc.get_holdings()


class TestAngelOneDataServicePositions:
    def test_get_positions_success(self, data_svc, mock_client):
        mock_client.get_positions = MagicMock(return_value=SAMPLE_POSITIONS)
        result = data_svc.get_positions()

        assert isinstance(result, AngelOnePositionsResponse)
        assert result.count == 1
        assert result.positions[0].symbol == "NIFTY23OCTFUT"
        assert result.positions[0].side == "BUY"  # net_qty > 0

    def test_get_positions_empty(self, data_svc, mock_client):
        """Empty positions is valid (no open trades)."""
        mock_client.get_positions = MagicMock(return_value=[])
        result = data_svc.get_positions()
        assert result.count == 0
        assert result.positions == []

    def test_get_positions_none(self, data_svc, mock_client):
        mock_client.get_positions = MagicMock(return_value=None)
        result = data_svc.get_positions()
        assert result.count == 0

    def test_get_positions_short_side(self, data_svc, mock_client):
        short_pos = [{**SAMPLE_POSITIONS[0], "netqty": "-2"}]
        mock_client.get_positions = MagicMock(return_value=short_pos)
        result = data_svc.get_positions()
        assert result.positions[0].side == "SELL"
        assert result.positions[0].quantity == Decimal("2")

    def test_get_positions_auth_failure(self, data_svc, mock_client):
        mock_client.get_positions = MagicMock(side_effect=AngelOneAuthenticationError("expired"))
        with pytest.raises(AngelOneAuthenticationError):
            data_svc.get_positions()


class TestAngelOneDataServiceOrders:
    def test_get_orders_success(self, data_svc, mock_client):
        mock_client.get_order_book = MagicMock(return_value=SAMPLE_ORDERS)
        result = data_svc.get_orders()

        assert isinstance(result, AngelOneOrdersResponse)
        assert result.count == 1
        order = result.orders[0]
        assert order.broker_order_id == "230101000000001"
        assert order.symbol == "TCS-EQ"
        assert order.side == "BUY"
        assert order.status == "complete"
        assert order.quantity == Decimal("5")

    def test_get_orders_empty(self, data_svc, mock_client):
        mock_client.get_order_book = MagicMock(return_value=[])
        result = data_svc.get_orders()
        assert result.count == 0

    def test_get_orders_none(self, data_svc, mock_client):
        mock_client.get_order_book = MagicMock(return_value=None)
        result = data_svc.get_orders()
        assert result.count == 0

    def test_get_orders_auth_failure(self, data_svc, mock_client):
        mock_client.get_order_book = MagicMock(side_effect=AngelOneAuthenticationError("expired"))
        with pytest.raises(AngelOneAuthenticationError):
            data_svc.get_orders()


# ===========================================================================
# Safety guard: no execution allowed
# ===========================================================================

class TestSafetyGuard:
    def test_live_trading_disabled(self):
        """ENABLE_LIVE_TRADING must remain False."""
        from app.core.config import settings
        assert settings.ENABLE_LIVE_TRADING is False

    def test_live_execution_unlocked_disabled(self):
        from app.core.config import settings
        assert settings.LIVE_EXECUTION_UNLOCKED is False

    def test_broker_execution_blocked(self):
        from app.core.config import settings
        assert settings.BROKER_EXECUTION_BLOCKED is True

    def test_client_place_order_always_blocked(self, mock_client):
        """AngelOneClient.place_order must always raise, even with a live session."""
        with pytest.raises((ValueError, NotImplementedError)):
            mock_client.place_order(symbol="TCS", qty=1, side="BUY")

    def test_client_modify_order_always_blocked(self, mock_client):
        with pytest.raises((ValueError, NotImplementedError)):
            mock_client.modify_order(order_id="123", qty=2)

    def test_client_cancel_order_always_blocked(self, mock_client):
        with pytest.raises((ValueError, NotImplementedError)):
            mock_client.cancel_order(order_id="123")

    def test_adapter_place_order_blocked(self, data_svc):
        """AngelOneDataService has NO place_order method — execution is impossible."""
        assert not hasattr(data_svc, "place_order"), (
            "AngelOneDataService must NOT expose a place_order method"
        )

    def test_adapter_modify_order_blocked(self, data_svc):
        assert not hasattr(data_svc, "modify_order"), (
            "AngelOneDataService must NOT expose a modify_order method"
        )

    def test_adapter_cancel_order_blocked(self, data_svc):
        assert not hasattr(data_svc, "cancel_order"), (
            "AngelOneDataService must NOT expose a cancel_order method"
        )


# ===========================================================================
# API endpoint integration tests  (mocked Angel One, real FastAPI routing)
# ===========================================================================

def _build_client_with_svc_override(base_client: TestClient, data_svc: AngelOneDataService):
    """Override get_angel_one_data_service dependency for a test."""
    from app.main import app
    from app.api.deps import get_angel_one_data_service
    app.dependency_overrides[get_angel_one_data_service] = lambda: data_svc
    return app


class TestBrokerMonitoringEndpoints:
    """Integration tests that override get_angel_one_data_service with a mock."""

    @pytest.fixture(autouse=True)
    def setup_svc_override(self, mock_client, monkeypatch):
        """Before each test, wire mock data service into the app DI."""
        from app.main import app
        from app.api.deps import get_angel_one_data_service

        svc = AngelOneDataService(mock_client)
        self._svc = svc
        self._mock_client = mock_client

        app.dependency_overrides[get_angel_one_data_service] = lambda: svc
        yield
        app.dependency_overrides.pop(get_angel_one_data_service, None)

    # -----------------------------------------------------------------------
    # Unauthenticated requests must return 401/403
    # -----------------------------------------------------------------------

    def test_account_unauthenticated(self, client: TestClient):
        resp = client.get("/api/v1/broker-monitoring/account")
        assert resp.status_code in (401, 403)

    def test_funds_unauthenticated(self, client: TestClient):
        resp = client.get("/api/v1/broker-monitoring/funds")
        assert resp.status_code in (401, 403)

    def test_holdings_unauthenticated(self, client: TestClient):
        resp = client.get("/api/v1/broker-monitoring/holdings")
        assert resp.status_code in (401, 403)

    def test_positions_unauthenticated(self, client: TestClient):
        resp = client.get("/api/v1/broker-monitoring/positions")
        assert resp.status_code in (401, 403)

    def test_orders_unauthenticated(self, client: TestClient):
        resp = client.get("/api/v1/broker-monitoring/orders")
        assert resp.status_code in (401, 403)

    # -----------------------------------------------------------------------
    # Authenticated — Angel One success
    # -----------------------------------------------------------------------

    def test_account_authenticated_success(self, client: TestClient, auth_headers: dict):
        self._mock_client.get_profile = MagicMock(return_value=SAMPLE_PROFILE)
        resp = client.get("/api/v1/broker-monitoring/account", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["client_id"] == "TESTCLIENT"
        assert data["broker"] == "ANGEL_ONE"
        # Safety: no secrets in response body
        assert "jwt_token" not in data
        assert "api_key" not in data
        assert "password" not in data
        assert "totp_secret" not in data
        assert "feed_token" not in data

    def test_funds_authenticated_success(self, client: TestClient, auth_headers: dict):
        self._mock_client.get_rms = MagicMock(return_value=SAMPLE_RMS)
        resp = client.get("/api/v1/broker-monitoring/funds", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["broker"] == "ANGEL_ONE"
        assert float(data["available_cash"]) == 50000.0
        assert data["currency"] == "INR"

    def test_holdings_authenticated_success(self, client: TestClient, auth_headers: dict):
        self._mock_client.get_holdings = MagicMock(return_value=SAMPLE_HOLDINGS)
        resp = client.get("/api/v1/broker-monitoring/holdings", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert data["holdings"][0]["symbol"] == "TCS-EQ"
        assert data["holdings"][0]["product"] == "DELIVERY"

    def test_positions_authenticated_success(self, client: TestClient, auth_headers: dict):
        self._mock_client.get_positions = MagicMock(return_value=SAMPLE_POSITIONS)
        resp = client.get("/api/v1/broker-monitoring/positions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["positions"][0]["symbol"] == "NIFTY23OCTFUT"

    def test_orders_authenticated_success(self, client: TestClient, auth_headers: dict):
        self._mock_client.get_order_book = MagicMock(return_value=SAMPLE_ORDERS)
        resp = client.get("/api/v1/broker-monitoring/orders", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["orders"][0]["broker_order_id"] == "230101000000001"

    # -----------------------------------------------------------------------
    # Authenticated — empty holdings / positions
    # -----------------------------------------------------------------------

    def test_holdings_empty(self, client: TestClient, auth_headers: dict):
        """Empty holdings must return 200 with empty list, not an error."""
        self._mock_client.get_holdings = MagicMock(return_value=[])
        resp = client.get("/api/v1/broker-monitoring/holdings", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["holdings"] == []

    def test_positions_empty(self, client: TestClient, auth_headers: dict):
        """Empty positions must return 200 with empty list, not an error."""
        self._mock_client.get_positions = MagicMock(return_value=[])
        resp = client.get("/api/v1/broker-monitoring/positions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["positions"] == []

    # -----------------------------------------------------------------------
    # Authenticated — Angel One API failure
    # -----------------------------------------------------------------------

    def test_holdings_auth_failure_returns_503(self, client: TestClient, auth_headers: dict):
        self._mock_client.get_holdings = MagicMock(
            side_effect=AngelOneAuthenticationError("session expired")
        )
        resp = client.get("/api/v1/broker-monitoring/holdings", headers=auth_headers)
        assert resp.status_code == 503
        # Ensure no secrets leaked in error detail
        body = resp.text
        assert "jwt" not in body.lower()
        assert "password" not in body.lower()
        assert "totp" not in body.lower()

    def test_funds_network_failure_returns_503(self, client: TestClient, auth_headers: dict):
        self._mock_client.get_rms = MagicMock(
            side_effect=AngelOneNetworkError("connection refused")
        )
        resp = client.get("/api/v1/broker-monitoring/funds", headers=auth_headers)
        assert resp.status_code == 503

    def test_orders_rate_limit_returns_429(self, client: TestClient, auth_headers: dict):
        self._mock_client.get_order_book = MagicMock(
            side_effect=AngelOneRateLimitError("too many requests")
        )
        resp = client.get("/api/v1/broker-monitoring/orders", headers=auth_headers)
        assert resp.status_code == 429

    def test_positions_invalid_response_returns_502(self, client: TestClient, auth_headers: dict):
        self._mock_client.get_positions = MagicMock(
            side_effect=AngelOneInvalidResponseError("bad JSON")
        )
        resp = client.get("/api/v1/broker-monitoring/positions", headers=auth_headers)
        assert resp.status_code == 502

    # -----------------------------------------------------------------------
    # auth-ping still returns CONNECTED when credentials are configured
    # -----------------------------------------------------------------------

    def test_auth_ping_still_works(self, client: TestClient, auth_headers: dict):
        """
        Verify that adding the 5 new endpoints did NOT break auth-ping.
        In test mode, BROKER_PROVIDER is 'paper', so paper mode path is taken.
        """
        resp = client.get("/api/v1/broker-monitoring/auth-ping", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "authenticated" in data
        assert "status" in data
        # live_trading_enabled must remain False
        assert data["live_trading_enabled"] is False

    # -----------------------------------------------------------------------
    # Confirm no execution methods available on response data
    # -----------------------------------------------------------------------

    def test_no_place_order_endpoint_exists(self, client: TestClient, auth_headers: dict):
        """There must be no POST /broker-monitoring/orders endpoint."""
        resp = client.post("/api/v1/broker-monitoring/orders", headers=auth_headers, json={})
        # FastAPI returns 405 (method not allowed) when GET exists but POST doesn't
        assert resp.status_code == 405  # Method Not Allowed

    def test_no_modify_order_endpoint(self, client: TestClient, auth_headers: dict):
        """PUT /orders/123 must not exist — confirms no order modification."""
        resp = client.put("/api/v1/broker-monitoring/orders/123", headers=auth_headers, json={})
        # 404 = path doesn't exist at all; 405 = path exists with different method
        assert resp.status_code in (404, 405)

    def test_no_cancel_order_endpoint(self, client: TestClient, auth_headers: dict):
        """DELETE /orders/123 must not exist — confirms no order cancellation."""
        resp = client.delete("/api/v1/broker-monitoring/orders/123", headers=auth_headers)
        assert resp.status_code in (404, 405)
