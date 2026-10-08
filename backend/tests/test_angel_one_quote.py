import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from app.services.market_data.angel_one import AngelOneMarketDataProvider
from app.services.brokers.angel_one.client import AngelOneClient
from app.schemas.market_data import MarketQuote

@pytest.fixture
def mock_client():
    client = MagicMock(spec=AngelOneClient)
    return client

@pytest.fixture
def provider(mock_client):
    AngelOneMarketDataProvider._master_mapping.clear()
    provider = AngelOneMarketDataProvider(mock_client)
    # inject a fake mapping using the class variable or the instance that points to it
    AngelOneMarketDataProvider._master_mapping["NSE:TCS"] = "11536"
    AngelOneMarketDataProvider._master_mapping["BSE:INFY"] = "1594"
    return provider

def test_successful_quote_parsing(provider, mock_client):
    mock_client.get_ltp_data.return_value = {
        "exchange": "NSE",
        "tradingsymbol": "TCS-EQ",
        "symboltoken": "11536",
        "open": 3000.0,
        "high": 3100.0,
        "low": 2900.0,
        "close": 2950.0,
        "ltp": 3050.0
    }
    
    quote = provider.get_quote("TCS", "NSE")
    assert quote is not None
    assert quote.symbol == "TCS"
    assert quote.exchange == "NSE"
    assert quote.price == 3050.0
    
def test_correct_token_resolution_bse(provider, mock_client):
    mock_client.get_ltp_data.return_value = {"ltp": 1500.0}
    quote = provider.get_quote("INFY", "BSE")
    assert quote.price == 1500.0
    mock_client.get_ltp_data.assert_called_once_with("BSE", "INFY", "1594")

def test_missing_token(provider, mock_client):
    quote = provider.get_quote("UNKNOWN", "NSE")
    assert quote is None

def test_malformed_broker_response(provider, mock_client):
    mock_client.get_ltp_data.return_value = {}
    assert provider.get_quote("TCS", "NSE") is None
    
def test_invalid_price(provider, mock_client):
    mock_client.get_ltp_data.return_value = {"ltp": -10.0}
    assert provider.get_quote("TCS", "NSE") is None

def test_high_less_than_low(provider, mock_client):
    mock_client.get_ltp_data.return_value = {"ltp": 3000.0, "high": 2900.0, "low": 3100.0}
    assert provider.get_quote("TCS", "NSE") is None

def test_unavailable_optional_fields(provider, mock_client):
    mock_client.get_ltp_data.return_value = {"ltp": 3000.0}
    quote = provider.get_quote("TCS", "NSE")
    assert quote is not None
    assert quote.price == 3000.0
    assert quote.open is None

def test_client_exception_handled(provider, mock_client):
    mock_client.get_ltp_data.side_effect = Exception("Network error")
    assert provider.get_quote("TCS", "NSE") is None

# --- New token resolution specific tests ---

@patch('app.services.discovery.scanner.MarketScanner.fetch_master_universe')
def test_mapping_resolves_exact_nse_equity(mock_fetch, mock_client):
    # - TCS NSE equity resolves successfully
    # - derivative token is not returned
    mock_fetch.return_value = [
        {"symbol": "TCS-EQ", "exch_seg": "NSE", "token": "11536", "instrumenttype": ""},
        {"symbol": "TCS24OCTFUT", "exch_seg": "NFO", "token": "12345", "instrumenttype": "FUTSTK"},
        {"symbol": "TCS-BE", "exch_seg": "NSE", "token": "99999", "instrumenttype": ""}
    ]
    
    # We create a new provider to trigger _ensure_mapping
    # but first we need to clear the class-level map
    AngelOneMarketDataProvider._master_mapping.clear()
    provider2 = AngelOneMarketDataProvider(mock_client)
    
    assert provider2._get_token("TCS", "NSE") == "11536"
    # derivative not mapped
    assert provider2._get_token("TCS24OCTFUT", "NSE") == ""
    # other series mapped with their full names if we wanted, but our logic only strips -EQ
    # meaning TCS-BE is NOT stripped to TCS
    assert provider2._get_token("TCS", "NSE") == "11536" 

@patch('app.services.discovery.scanner.MarketScanner.fetch_master_universe')
def test_mapping_bse_not_returned_for_nse(mock_fetch, mock_client):
    mock_fetch.return_value = [
        {"symbol": "TCS", "exch_seg": "BSE", "token": "532540", "instrumenttype": ""}
    ]
    AngelOneMarketDataProvider._master_mapping.clear()
    provider2 = AngelOneMarketDataProvider(mock_client)
    
    assert provider2._get_token("TCS", "NSE") == ""
    assert provider2._get_token("TCS", "BSE") == "532540"

@patch('app.services.discovery.scanner.MarketScanner.fetch_master_universe')
def test_mapping_ambiguous_fails_safely(mock_fetch, mock_client):
    # E.g. BSE might have two TCS mappings (if that's even possible), it shouldn't overwrite the first.
    mock_fetch.return_value = [
        {"symbol": "TCS", "exch_seg": "BSE", "token": "532540", "instrumenttype": ""},
        {"symbol": "TCS", "exch_seg": "BSE", "token": "999999", "instrumenttype": ""}
    ]
    AngelOneMarketDataProvider._master_mapping.clear()
    provider2 = AngelOneMarketDataProvider(mock_client)
    
    # Keeps the first one
    assert provider2._get_token("TCS", "BSE") == "532540"

def test_no_hardcoded_token(provider):
    # Verify the code doesn't just have if symbol == "TCS": return "11536"
    AngelOneMarketDataProvider._master_mapping.clear()
    # Now map is empty
    assert provider._get_token("TCS", "NSE") == ""
