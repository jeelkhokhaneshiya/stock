"""
test_monitoring_auth_and_telegram.py
====================================
Tests for:
1. Expired/invalid token handling in AngelOneClient with single re-authentication retry.
2. Re-authentication failure when credentials fail or broker continually rejects.
3. Telegram notification failure handling in production (never reported as mock delivered).
4. Strict read-only boundary for MonitoringWorker (no OrderIntent creation or broker execution).
"""

import pytest
import os
import json
from unittest.mock import MagicMock, patch
import httpx

from app.core.config import settings
from app.services.brokers.angel_one.auth import AngelOneAuth
from app.services.brokers.angel_one.client import AngelOneClient
from app.services.brokers.angel_one.exceptions import (
    AngelOneAuthenticationError,
    AngelOneInvalidResponseError,
)
from app.services.notification_service import (
    TelegramNotificationService,
    MockNotificationService,
    FailedNotificationService,
    get_notification_service,
)
from app.worker.monitoring_worker import MonitoringWorker, STATE_FILE


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def auth():
    a = AngelOneAuth("TEST_KEY", "TEST_CLIENT", "TEST_PASS", "TEST_TOTP_SECRET")
    a.set_tokens("INITIAL_EXPIRED_JWT", "refresh", "feed")
    return a


@pytest.fixture
def client(auth):
    return AngelOneClient(auth)


def _make_response(status_code: int, json_body: dict | None = None, text: str = "") -> httpx.Response:
    request = httpx.Request("GET", "https://apiconnect.angelone.in/test")
    if json_body is not None:
        content = json.dumps(json_body).encode("utf-8")
        headers = {"content-type": "application/json"}
    else:
        content = text.encode("utf-8")
        headers = {"content-type": "text/plain"}
    return httpx.Response(status_code=status_code, content=content, headers=headers, request=request)


# ---------------------------------------------------------------------------
# Tests: Token expiry and re-authentication
# ---------------------------------------------------------------------------

def test_expired_token_triggers_single_reauth_and_succeeds(client):
    """
    When an API call returns 401/403 or AG8001 (Invalid Token),
    AngelOneClient should safely re-authenticate once and retry the read-only request.
    """
    invalid_token_resp = _make_response(
        200,
        json_body={"status": False, "message": "Invalid Token", "errorcode": "AG8001", "data": {}}
    )
    success_resp = _make_response(
        200,
        json_body={"status": True, "message": "SUCCESS", "errorcode": "", "data": {"net": "15000.00"}}
    )

    with patch.object(client.http_client, "get", side_effect=[invalid_token_resp, success_resp]) as mock_get:
        with patch.object(client, "authenticate") as mock_auth:
            # When authenticate is called, simulate setting a fresh token
            def do_auth(force=False):
                client.auth.set_tokens("FRESH_JWT_TOKEN", "new_ref", "new_feed")
                return True
            mock_auth.side_effect = do_auth

            rms_data = client.get_rms()

            assert rms_data == {"net": "15000.00"}
            assert mock_auth.call_count == 1
            # Verify force=True was passed to bypass stale cooldown on invalid token
            assert mock_auth.call_args[1].get("force") is True
            assert mock_get.call_count == 2


def test_reauth_failure_raises_authentication_error(client):
    """
    If re-authentication itself fails (e.g., broker rejects login credentials),
    the error should be raised and not caught in an infinite retry loop.
    """
    invalid_token_resp = _make_response(
        200,
        json_body={"status": False, "message": "Invalid Token", "errorcode": "AG8001", "data": {}}
    )

    with patch.object(client.http_client, "get", return_value=invalid_token_resp):
        with patch.object(client, "authenticate", side_effect=AngelOneAuthenticationError("Login failed: bad credentials")):
            with pytest.raises(AngelOneAuthenticationError) as exc_info:
                client.get_rms()
            assert "Login failed" in str(exc_info.value)


def test_consecutive_invalid_tokens_aborts_after_one_reauth(client):
    """
    If the request still returns Invalid Token after re-authenticating,
    it must NOT retry again and must raise AngelOneAuthenticationError.
    """
    invalid_token_resp = _make_response(
        200,
        json_body={"status": False, "message": "Invalid Token", "errorcode": "AG8001", "data": {}}
    )

    with patch.object(client.http_client, "get", return_value=invalid_token_resp) as mock_get:
        with patch.object(client, "authenticate") as mock_auth:
            def do_auth(force=False):
                client.auth.set_tokens("NEW_JWT_TOKEN", "ref", "feed")
                return True
            mock_auth.side_effect = do_auth

            with pytest.raises(AngelOneAuthenticationError):
                client.get_rms()

            # Attempt 0 got invalid token -> authenticate called once -> retry attempt 1 got invalid token -> raises
            assert mock_auth.call_count == 1
            assert mock_get.call_count == 2



# ---------------------------------------------------------------------------
# Tests: Telegram delivery and mock prevention in production
# ---------------------------------------------------------------------------

def test_telegram_delivery_failure_returns_false():
    """TelegramNotificationService returns False and logs an error when HTTP sending fails."""
    service = TelegramNotificationService(bot_token="invalid_token", chat_id="12345")
    with patch("httpx.post", side_effect=httpx.HTTPError("Connection failed")):
        result = service.send_notification("Test notification")
        assert result is False


def test_telegram_missing_credentials_returns_false(monkeypatch):
    """TelegramNotificationService returns False when token or chat id is missing."""
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", None)
    monkeypatch.setattr(settings, "TELEGRAM_CHAT_ID", None)
    service = TelegramNotificationService(bot_token="", chat_id="")
    result = service.send_notification("Test notification")
    assert result is False



def test_failed_notification_service_in_production_without_creds(monkeypatch):
    """
    In production (TESTING=False), if Telegram credentials are missing,
    get_notification_service() must return FailedNotificationService,
    NEVER MockNotificationService, and send_notification must return False.
    """
    monkeypatch.setattr(settings, "TESTING", False)
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", None)
    monkeypatch.setattr(settings, "TELEGRAM_CHAT_ID", None)

    service = get_notification_service()
    assert isinstance(service, FailedNotificationService)
    assert not isinstance(service, MockNotificationService)
    assert service.send_notification("Alert") is False


def test_mock_notification_service_only_used_when_testing_is_true(monkeypatch):
    """MockNotificationService is only returned when TESTING is True."""
    monkeypatch.setattr(settings, "TESTING", True)
    service = get_notification_service()
    assert isinstance(service, MockNotificationService)
    assert service.send_notification("Test Alert") is True


# ---------------------------------------------------------------------------
# Tests: Strict read-only boundary
# ---------------------------------------------------------------------------

def test_monitoring_worker_strictly_read_only():
    """
    The MonitoringWorker must be strictly read-only:
    - Never import or instantiate OrderIntent
    - Never call confirm_order or execute_confirmed_order
    - Live order placement methods on AngelOneClient must always raise
    """
    with open("app/worker/monitoring_worker.py", "r", encoding="utf-8") as f:
        worker_code = f.read()

    assert "OrderIntent" not in worker_code
    assert "execute_confirmed_order" not in worker_code
    assert "confirm_order" not in worker_code
    assert "place_order" not in worker_code

    auth = AngelOneAuth("TEST", "TEST", "TEST", "TEST")
    client = AngelOneClient(auth)

    with pytest.raises(Exception):
        client.place_order()
    with pytest.raises(Exception):
        client.modify_order()
    with pytest.raises(Exception):
        client.cancel_order()
