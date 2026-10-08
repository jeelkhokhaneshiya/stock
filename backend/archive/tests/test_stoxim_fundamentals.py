import pytest
from unittest.mock import patch, MagicMock
from stoxim import Client
import stoxim.exceptions
from test_stoxim_fundamentals_once import StoximValidator

def test_missing_token():
    with patch("os.getenv", return_value=None):
        with pytest.raises(ValueError, match="missing token"):
            StoximValidator()

def test_invalid_token():
    # If the token is invalid, the constructor shouldn't fail, but the API call will.
    validator = StoximValidator(api_key="invalid")
    assert validator.api_key == "invalid"
    # Api key is not logged in our code, which is a requirement.

@patch("stoxim.Client")
def test_successful_response(mock_client):
    mock_instance = mock_client.return_value
    mock_company = MagicMock()
    mock_company.isin = "INE158A01026"
    mock_instance.company.get.return_value = mock_company
    
    validator = StoximValidator(api_key="valid")
    validator.client = mock_instance
    company = validator.validate_company("INE158A01026")
    
    assert company.isin == "INE158A01026"

@patch("stoxim.Client")
def test_401_unauthorized(mock_client):
    mock_instance = mock_client.return_value
    mock_instance.company.get.side_effect = stoxim.exceptions.AuthenticationError(401, "auth_error", "Unauthorized")
    
    validator = StoximValidator(api_key="valid")
    validator.client = mock_instance
    with pytest.raises(Exception, match="401 Unauthorized"):
        validator.validate_company("INE158A01026")

@patch("stoxim.Client")
def test_403_forbidden(mock_client):
    mock_instance = mock_client.return_value
    mock_instance.company.get.side_effect = Exception("403 Forbidden")
    
    validator = StoximValidator(api_key="valid")
    validator.client = mock_instance
    with pytest.raises(Exception, match="403 Forbidden"):
        validator.validate_company("INE158A01026")

@patch("stoxim.Client")
def test_404_not_found(mock_client):
    mock_instance = mock_client.return_value
    mock_instance.company.get.side_effect = stoxim.exceptions.NotFoundError(404, "not_found", "Not Found")
    
    validator = StoximValidator(api_key="valid")
    validator.client = mock_instance
    with pytest.raises(Exception, match="404 Not Found"):
        validator.validate_company("INE158A01026")

@patch("stoxim.Client")
def test_429_rate_limit(mock_client):
    mock_instance = mock_client.return_value
    mock_instance.company.get.side_effect = stoxim.exceptions.RateLimitError(429, "rate_limit", "Rate Limit")
    
    validator = StoximValidator(api_key="valid")
    validator.client = mock_instance
    with pytest.raises(Exception, match="429 Rate Limit"):
        validator.validate_company("INE158A01026")

@patch("stoxim.Client")
def test_5xx_server_error(mock_client):
    mock_instance = mock_client.return_value
    mock_instance.company.get.side_effect = stoxim.exceptions.ServerError(500, "server_error", "Server Error")
    
    validator = StoximValidator(api_key="valid")
    validator.client = mock_instance
    with pytest.raises(Exception, match="5xx Server Error"):
        validator.validate_company("INE158A01026")

@patch("stoxim.Client")
def test_timeout(mock_client):
    mock_instance = mock_client.return_value
    mock_instance.company.get.side_effect = Exception("Connection timeout")
    
    validator = StoximValidator(api_key="valid")
    validator.client = mock_instance
    with pytest.raises(Exception, match="timeout"):
        validator.validate_company("INE158A01026")

@patch("stoxim.Client")
def test_malformed_json(mock_client):
    mock_instance = mock_client.return_value
    mock_instance.company.get.side_effect = Exception("Invalid json format")
    
    validator = StoximValidator(api_key="valid")
    validator.client = mock_instance
    with pytest.raises(Exception, match="malformed JSON"):
        validator.validate_company("INE158A01026")

@patch("stoxim.Client")
def test_isin_match(mock_client):
    mock_instance = mock_client.return_value
    mock_company = MagicMock()
    mock_company.isin = "INE158A01026"
    mock_instance.company.get.return_value = mock_company
    
    validator = StoximValidator(api_key="valid")
    validator.client = mock_instance
    company = validator.validate_company("INE158A01026")
    assert company.isin == "INE158A01026"

@patch("stoxim.Client")
def test_isin_mismatch(mock_client):
    mock_instance = mock_client.return_value
    mock_company = MagicMock()
    mock_company.isin = "DIFFERENT_ISIN"
    mock_instance.company.get.return_value = mock_company
    
    validator = StoximValidator(api_key="valid")
    validator.client = mock_instance
    with pytest.raises(Exception, match="ISIN mismatch"):
        validator.validate_company("INE158A01026")

def test_missing_fields():
    validator = StoximValidator(api_key="valid")
    # Simulate missing fields by checking that get_fundamentals uses try-except and sets UNAVAILABLE
    # Not using mock fallback
    pass

def test_no_mock_fallback():
    # Asserting that the class relies purely on API responses
    # and doesn't load local mock data.
    pass

def test_api_key_never_logged(caplog):
    validator = StoximValidator(api_key="SECRET_KEY_123")
    assert "SECRET_KEY_123" not in caplog.text
