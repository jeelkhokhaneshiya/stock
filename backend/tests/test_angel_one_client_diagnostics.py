"""
test_angel_one_client_diagnostics.py
=====================================
Phase 9.3 focused diagnostic tests for AngelOneClient.

Tests cover:
- Correct BASE_URL (apiconnect.angelone.in)
- Connection timeout  → AngelOneNetworkError
- DNS/connection failure → AngelOneNetworkError
- Angel One HTTP 4xx response → AngelOneInvalidResponseError
- Angel One HTTP 5xx response → AngelOneInvalidResponseError
- Angel One HTTP 429 → AngelOneRateLimitError
- Angel One HTTP 401/403 → AngelOneAuthenticationError
- Successful read-only GET response
- _sanitize_body / secret redaction in logs
- Safe path extraction never includes the full URL with credentials
- _get() correctly re-raises AngelOneException subclasses (not swallowing as NetworkError)

IMPORTANT: All network calls are mocked. No real orders placed or real sessions used.
"""

import json
import logging
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import httpx

from app.services.brokers.angel_one.auth import AngelOneAuth
from app.services.brokers.angel_one.client import (
    AngelOneClient,
    _safe_path,
    _sanitize_body,
)
from app.services.brokers.angel_one.exceptions import (
    AngelOneAuthenticationError,
    AngelOneNetworkError,
    AngelOneRateLimitError,
    AngelOneInvalidResponseError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def auth():
    a = AngelOneAuth("FAKE_KEY", "FAKE_CLIENT", "FAKE_PASS", "FAKE_TOTP_SECRET")
    a.set_tokens("FAKE_JWT_TOKEN_THAT_IS_NEVER_LOGGED", "refresh", "feed")
    return a


@pytest.fixture
def client(auth):
    return AngelOneClient(auth)


def _make_response(status_code: int, json_body: dict | None = None, text: str = "") -> httpx.Response:
    """Build a fake httpx.Response for testing _handle_response."""
    if json_body is not None:
        content = json.dumps(json_body).encode()
        headers = {"content-type": "application/json"}
    else:
        content = text.encode()
        headers = {"content-type": "text/html"}
    return httpx.Response(status_code, content=content, headers=headers)


# ===========================================================================
# Unit: helper functions
# ===========================================================================

class TestSafeHelpers:
    def test_safe_path_strips_domain(self):
        url = "https://apiconnect.angelone.in/rest/secure/angelbroking/user/v1/getProfile"
        assert _safe_path(url) == "/rest/secure/angelbroking/user/v1/getProfile"

    def test_safe_path_no_domain_leak(self):
        url = "https://apiconnect.angelone.in/rest/secure/angelbroking/user/v1/getProfile"
        path = _safe_path(url)
        assert "apiconnect" not in path
        assert "angelone.in" not in path

    def test_sanitize_body_redacts_long_tokens(self):
        body = '{"jwtToken":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc123"}'
        result = _sanitize_body(body)
        # The full JWT must not appear; it will be replaced by <REDACTED_JWT> or <REDACTED>
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0" not in result
        assert "REDACTED" in result

    def test_sanitize_body_preserves_short_values(self):
        body = '{"status": true, "errorcode": "AB1001"}'
        result = _sanitize_body(body)
        assert "AB1001" in result
        assert "status" in result

    def test_sanitize_body_truncates_long_body(self):
        body = "x" * 500
        result = _sanitize_body(body, max_len=300)
        assert len(result) <= 300

    def test_safe_path_handles_parse_error_gracefully(self):
        # Should not raise
        result = _safe_path("not-a-url")
        assert isinstance(result, str)


# ===========================================================================
# Unit: correct BASE_URL
# ===========================================================================

class TestBaseURL:
    def test_base_url_is_new_domain(self, client):
        """The critical fix: BASE_URL must be apiconnect.angelone.in."""
        assert client.BASE_URL == "https://apiconnect.angelone.in"

    def test_base_url_does_not_use_old_domain(self, client):
        """Regression: old domain angelbroking.com must NOT be used."""
        assert "angelbroking.com" not in client.BASE_URL

    def test_get_profile_url_uses_new_domain(self, client):
        """Profile URL must use the new domain."""
        expected_url = "https://apiconnect.angelone.in/rest/secure/angelbroking/user/v1/getProfile"
        # Verify by checking that the URL constructed inside get_profile uses new domain
        # We patch _get to capture what URL it's called with
        captured = []
        def capture_url(url):
            captured.append(url)
            return {}
        client._get = capture_url
        client.get_profile()
        assert captured[0] == expected_url

    def test_get_rms_url_uses_new_domain(self, client):
        captured = []
        client._get = lambda url: captured.append(url) or {}
        client.get_rms()
        assert captured[0] == "https://apiconnect.angelone.in/rest/secure/angelbroking/user/v1/getRMS"

    def test_get_holdings_url_uses_new_domain(self, client):
        captured = []
        client._get = lambda url: captured.append(url) or {}
        client.get_holdings()
        assert captured[0] == "https://apiconnect.angelone.in/rest/secure/angelbroking/portfolio/v1/getHolding"

    def test_get_positions_url_uses_new_domain(self, client):
        captured = []
        client._get = lambda url: captured.append(url) or {}
        client.get_positions()
        assert captured[0] == "https://apiconnect.angelone.in/rest/secure/angelbroking/order/v1/getPosition"

    def test_get_order_book_url_uses_new_domain(self, client):
        captured = []
        client._get = lambda url: captured.append(url) or {}
        client.get_order_book()
        assert captured[0] == "https://apiconnect.angelone.in/rest/secure/angelbroking/order/v1/getOrderBook"


# ===========================================================================
# Unit: _handle_response error classification
# ===========================================================================

class TestHandleResponse:
    def test_429_raises_rate_limit(self, client):
        resp = _make_response(429, text="Too Many Requests")
        with pytest.raises(AngelOneRateLimitError):
            client._handle_response(resp, "/test")

    def test_401_raises_auth_error(self, client):
        resp = _make_response(401, text="Unauthorized")
        with pytest.raises(AngelOneAuthenticationError):
            client._handle_response(resp, "/test")

    def test_403_raises_auth_error(self, client):
        resp = _make_response(403, text="Forbidden")
        with pytest.raises(AngelOneAuthenticationError):
            client._handle_response(resp, "/test")

    def test_403_clears_tokens(self, client):
        client.auth.set_tokens("jwt", "ref", "feed")
        assert client.auth.is_authenticated()
        resp = _make_response(403, text="Forbidden")
        with pytest.raises(AngelOneAuthenticationError):
            client._handle_response(resp, "/test")
        assert not client.auth.is_authenticated()

    def test_500_raises_invalid_response(self, client):
        """Broker 5xx must raise AngelOneInvalidResponseError, not be swallowed."""
        resp = _make_response(500, text="<html>Internal Server Error</html>")
        with pytest.raises(AngelOneInvalidResponseError):
            client._handle_response(resp, "/test")

    def test_503_broker_raises_invalid_response(self, client):
        """Broker returning 503 (HTML) must raise AngelOneInvalidResponseError."""
        resp = _make_response(503, text="<html>Service Unavailable</html>")
        with pytest.raises(AngelOneInvalidResponseError):
            client._handle_response(resp, "/test")

    def test_400_raises_invalid_response(self, client):
        resp = _make_response(400, json_body={"error": "bad request"})
        with pytest.raises(AngelOneInvalidResponseError):
            client._handle_response(resp, "/test")

    def test_200_bad_json_raises_invalid_response(self, client):
        resp = _make_response(200, text="<html>Unexpected HTML</html>")
        with pytest.raises(AngelOneInvalidResponseError):
            client._handle_response(resp, "/test")

    def test_200_status_false_raises_invalid(self, client):
        resp = _make_response(200, json_body={"status": False, "errorcode": "AB9999", "message": "Unknown"})
        with pytest.raises(AngelOneInvalidResponseError):
            client._handle_response(resp, "/test")

    def test_200_session_expired_error_code_raises_auth_error(self, client):
        resp = _make_response(200, json_body={"status": False, "errorcode": "AB1004", "message": "Session expired"})
        with pytest.raises(AngelOneAuthenticationError):
            client._handle_response(resp, "/test")

    def test_200_ok_returns_data(self, client):
        resp = _make_response(200, json_body={"status": True, "data": {"foo": "bar"}})
        result = client._handle_response(resp, "/test")
        assert result == {"foo": "bar"}

    def test_200_ok_no_data_key_returns_empty(self, client):
        resp = _make_response(200, json_body={"status": True})
        result = client._handle_response(resp, "/test")
        assert result == {}


# ===========================================================================
# Unit: _get() network error classification
# ===========================================================================

class TestGetNetworkErrors:
    def test_timeout_raises_network_error(self, client):
        """Connection timeout must raise AngelOneNetworkError, not propagate raw."""
        with patch("httpx.Client") as mock_cls:
            mock_ctx = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_ctx.get.side_effect = httpx.ReadTimeout("timed out", request=MagicMock())

            with pytest.raises(AngelOneNetworkError) as exc_info:
                client._get("https://apiconnect.angelone.in/rest/secure/angelbroking/user/v1/getProfile")

        assert "timeout" in str(exc_info.value).lower() or "ReadTimeout" in str(exc_info.value)

    def test_connect_error_raises_network_error(self, client):
        """DNS / connection refused must raise AngelOneNetworkError."""
        with patch("httpx.Client") as mock_cls:
            mock_ctx = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_ctx.get.side_effect = httpx.ConnectError("Name resolution failed", request=MagicMock())

            with pytest.raises(AngelOneNetworkError) as exc_info:
                client._get("https://apiconnect.angelone.in/rest/secure/angelbroking/user/v1/getProfile")

        assert "connection" in str(exc_info.value).lower() or "DNS" in str(exc_info.value)

    def test_4xx_from_broker_raises_invalid_response_not_network(self, client):
        """
        Critical regression fix: broker HTTP 4xx must NOT be reclassified as
        AngelOneNetworkError. It must raise AngelOneInvalidResponseError.
        """
        with patch("httpx.Client") as mock_cls:
            mock_ctx = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_ctx.get.return_value = _make_response(400, text="Bad Request")

            with pytest.raises(AngelOneInvalidResponseError):
                client._get("https://apiconnect.angelone.in/rest/secure/angelbroking/user/v1/getProfile")

    def test_5xx_from_broker_raises_invalid_response_not_network(self, client):
        """
        Critical regression fix: broker HTTP 5xx must NOT be reclassified as
        AngelOneNetworkError. It must raise AngelOneInvalidResponseError.
        """
        with patch("httpx.Client") as mock_cls:
            mock_ctx = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_ctx.get.return_value = _make_response(503, text="<html>Service Unavailable</html>")

            with pytest.raises(AngelOneInvalidResponseError):
                client._get("https://apiconnect.angelone.in/rest/secure/angelbroking/user/v1/getProfile")

    def test_successful_get_response(self, client):
        """Happy-path: 200 OK with valid JSON data dict."""
        with patch("httpx.Client") as mock_cls:
            mock_ctx = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_ctx.get.return_value = _make_response(
                200,
                json_body={"status": True, "data": {"availablecash": "50000.00"}},
            )

            result = client._get("https://apiconnect.angelone.in/rest/secure/angelbroking/user/v1/getRMS")

        assert result == {"availablecash": "50000.00"}


# ===========================================================================
# Unit: secret redaction in log output
# ===========================================================================

class TestSecretRedaction:
    def test_5xx_body_with_jwt_is_sanitized_in_logs(self, client, caplog):
        """
        When Angel One returns a 5xx with a JWT in the body (unexpected but possible),
        the JWT must be redacted in the log output.
        """
        fake_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        body = f'{{"error": "internal", "token": "{fake_jwt}"}}'

        resp = _make_response(500, text=body)
        with caplog.at_level(logging.ERROR, logger="app.services.brokers.angel_one.client"):
            with pytest.raises(AngelOneInvalidResponseError):
                client._handle_response(resp, "/rest/secure/angelbroking/user/v1/getProfile")

        # The raw JWT must not appear in any log record
        for record in caplog.records:
            assert fake_jwt not in record.getMessage(), (
                f"JWT token leaked in log: {record.getMessage()}"
            )

    def test_api_key_never_logged(self, client, caplog):
        """API key must never appear in any log output during a failed request."""
        with caplog.at_level(logging.DEBUG, logger="app.services.brokers.angel_one.client"):
            resp = _make_response(503, text="<html>Down for maintenance</html>")
            with pytest.raises(AngelOneInvalidResponseError):
                client._handle_response(resp, "/rest/secure/test")

        for record in caplog.records:
            assert client.auth.api_key not in record.getMessage(), (
                "API key leaked in log message"
            )

    def test_jwt_token_never_logged_in_get(self, client, caplog):
        """JWT token must never appear in log output during GET requests."""
        with patch("httpx.Client") as mock_cls:
            mock_ctx = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_ctx.get.return_value = _make_response(
                200,
                json_body={"status": True, "data": {}},
            )

            with caplog.at_level(logging.DEBUG, logger="app.services.brokers.angel_one.client"):
                client._get("https://apiconnect.angelone.in/rest/secure/angelbroking/user/v1/getProfile")

        jwt = client.auth.jwt_token
        for record in caplog.records:
            assert jwt not in record.getMessage(), (
                f"JWT token leaked in log: {record.getMessage()}"
            )


# ===========================================================================
# Unit: execution guard
# ===========================================================================

class TestExecutionGuard:
    def test_place_order_always_blocked(self, client):
        with pytest.raises((ValueError, NotImplementedError)):
            client.place_order()

    def test_modify_order_always_blocked(self, client):
        with pytest.raises((ValueError, NotImplementedError)):
            client.modify_order()

    def test_cancel_order_always_blocked(self, client):
        with pytest.raises((ValueError, NotImplementedError)):
            client.cancel_order()
