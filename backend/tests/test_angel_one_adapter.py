import pytest
from unittest.mock import Mock
from decimal import Decimal
from app.services.brokers.angel_one.auth import AngelOneAuth
from app.services.brokers.angel_one.client import AngelOneClient
from app.services.brokers.angel_one.adapter import AngelOneAdapter
from app.services.brokers.angel_one.exceptions import AngelOneAuthenticationError

@pytest.fixture
def auth():
    return AngelOneAuth("key", "client", "pass", "secret")

@pytest.fixture
def client(auth):
    client = AngelOneClient(auth)
    client.authenticate = Mock(return_value=True)
    return client

@pytest.fixture
def adapter(client):
    return AngelOneAdapter(client)

def test_angel_one_auth_missing_totp():
    auth = AngelOneAuth("key", "client", "pass", "")
    with pytest.raises(AngelOneAuthenticationError):
        auth.generate_totp()

def test_angel_one_auth_headers(auth):
    auth.set_tokens("jwt", "ref", "feed")
    headers = auth.get_auth_headers()
    assert headers["Authorization"] == "Bearer jwt"
    assert headers["X-PrivateKey"] == "key"

def test_adapter_cash_mapping(adapter, client):
    client.get_rms = Mock(return_value={"availablecash": "100.5", "utilisedmargin": "50.0", "netcashaval": "150.5"})
    cash = adapter.get_available_cash()
    assert cash.available_cash == Decimal("100.5")
    assert cash.used_cash == Decimal("50.0")

def test_adapter_holdings_mapping(adapter, client):
    client.get_holdings = Mock(return_value=[{
        "tradingsymbol": "TCS",
        "quantity": "10",
        "averageprice": "3000.0",
        "product": "DELIVERY"
    }])
    holdings = adapter.get_holdings()
    assert len(holdings) == 1
    assert holdings[0].symbol == "TCS"
    assert holdings[0].quantity == Decimal("10")
    assert holdings[0].product == "DELIVERY"

def test_adapter_orders_mapping(adapter, client):
    client.get_order_book = Mock(return_value=[{
        "orderid": "12345",
        "tradingsymbol": "INFY",
        "transactiontype": "BUY",
        "quantity": "5",
        "price": "1500.0",
        "status": "completed",
        "producttype": "DELIVERY"
    }])
    orders = adapter.get_orders()
    assert len(orders) == 1
    assert orders[0].broker_order_id == "12345"
    assert orders[0].symbol == "INFY"
    assert orders[0].price == Decimal("1500.0")

def test_live_order_blocked(adapter):
    with pytest.raises(ValueError, match="LIVE_TRADING_DISABLED"):
        adapter.place_order(symbol="TCS", qty=1)
