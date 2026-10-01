import httpx
import logging
import json
from typing import Dict, Any
from app.services.brokers.angel_one.auth import AngelOneAuth
from app.services.brokers.angel_one.exceptions import (
    AngelOneAuthenticationError, AngelOneNetworkError,
    AngelOneRateLimitError, AngelOneInvalidResponseError,
    AngelOneException,
)
from app.services.brokers.guard import LiveBrokerExecutionGuard

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Safe diagnostic helpers — NEVER log secrets
# ---------------------------------------------------------------------------

def _safe_path(url: str) -> str:
    """Return only the path portion of a URL (strips domain, no query params)."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.path
    except Exception:
        return "<url-parse-error>"


def _sanitize_body(body: str, max_len: int = 300) -> str:
    """
    Return a safe excerpt of a response body.
    Replaces credential-like strings with <REDACTED>.
    Never returns more than max_len characters.

    Patterns redacted:
    - Dot-separated base64url JWT tokens (eyJ...eyJ...sig)
    - Long base64/hex strings >= 30 chars
    """
    import re
    # Redact full JWTs: three base64url segments separated by dots
    sanitized = re.sub(
        r'eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]*',
        '<REDACTED_JWT>',
        body,
    )
    # Redact any remaining long credential-like tokens (>= 30 contiguous chars)
    sanitized = re.sub(r'[A-Za-z0-9+/=_\-]{30,}', '<REDACTED>', sanitized)
    return sanitized[:max_len]


class AngelOneClient:
    # -----------------------------------------------------------------------
    # ROOT-CAUSE FIX (Phase 9.3):
    # The old domain `apiconnect.angelbroking.com` has been migrated by
    # Angel One.  The correct current domain is `apiconnect.angelone.in`.
    # Using the old domain caused connection/TLS errors on secure endpoints
    # that were silently caught as AngelOneNetworkError → HTTP 503.
    # The login endpoint appeared to work intermittently because the old
    # domain may still forward auth POSTs, but secure GETs were failing.
    # -----------------------------------------------------------------------
    BASE_URL = "https://apiconnect.angelone.in"

    # Login still uses the old path structure which works on the new domain:
    # POST /rest/auth/angelbroking/user/v1/loginByPassword

    def __init__(self, auth: AngelOneAuth):
        self.auth = auth
        self.timeout = httpx.Timeout(15.0, connect=8.0)

    # -----------------------------------------------------------------------
    # Response handling
    # -----------------------------------------------------------------------

    def _handle_response(self, response: httpx.Response, path: str = "") -> Dict[str, Any]:
        status = response.status_code
        logger.debug("Angel One API response: method=GET path=%s status=%d", path, status)

        if status == 429:
            logger.warning("Angel One rate limit hit: path=%s", path)
            raise AngelOneRateLimitError("Rate limit exceeded")

        if status in (401, 403):
            logger.warning("Angel One auth rejected: path=%s status=%d", path, status)
            self.auth.clear_tokens()
            raise AngelOneAuthenticationError(f"Authentication rejected by broker: {status}")

        if status >= 500:
            # Broker-side server error — try to log safe body excerpt
            try:
                excerpt = _sanitize_body(response.text)
            except Exception:
                excerpt = "<unreadable>"
            logger.error(
                "Angel One server error: path=%s status=%d body_excerpt=%s",
                path, status, excerpt,
            )
            raise AngelOneInvalidResponseError(
                f"Angel One server error {status} on {path}"
            )

        if status >= 400:
            # Other 4xx (e.g. 400 Bad Request, 404)
            try:
                excerpt = _sanitize_body(response.text)
            except Exception:
                excerpt = "<unreadable>"
            logger.warning(
                "Angel One client error: path=%s status=%d body_excerpt=%s",
                path, status, excerpt,
            )
            raise AngelOneInvalidResponseError(
                f"Angel One client error {status} on {path}"
            )

        try:
            data = response.json()
        except json.JSONDecodeError:
            logger.error(
                "Angel One returned non-JSON: path=%s status=%d body_excerpt=%s",
                path, status, _sanitize_body(response.text),
            )
            raise AngelOneInvalidResponseError("Invalid JSON response from broker")

        if not data.get("status"):
            error_code = data.get("errorcode", "UNKNOWN")
            message = data.get("message", "Unknown error")
            logger.warning(
                "Angel One API error payload: path=%s errorcode=%s message=%s",
                path, error_code, message,
            )
            if error_code in ["AB1004", "AB1010", "AB1017", "AG8001"]:
                self.auth.clear_tokens()
                raise AngelOneAuthenticationError(
                    f"Session expired or invalid: errorcode={error_code}"
                )
            raise AngelOneInvalidResponseError(
                f"Broker API error: errorcode={error_code}"
            )

        return data.get("data", {})

    # -----------------------------------------------------------------------
    # Authentication
    # -----------------------------------------------------------------------

    def authenticate(self) -> bool:
        """Authenticate using SmartAPI loginByPassword endpoint."""
        url = f"{self.BASE_URL}/rest/auth/angelbroking/user/v1/loginByPassword"
        path = _safe_path(url)

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "00:00:00:00:00:00",
            "X-PrivateKey": self.auth.api_key,  # stays server-side; never logged
        }

        payload = {
            "clientcode": self.auth.client_id,
            "password": self.auth.password,
            "totp": self.auth.generate_totp(),
        }

        logger.debug("Angel One authenticate: method=POST path=%s", path)
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, headers=headers, json=payload)

            data = self._handle_response(response, path)

            self.auth.set_tokens(
                jwt_token=data.get("jwtToken"),
                refresh_token=data.get("refreshToken"),
                feed_token=data.get("feedToken"),
            )
            logger.info("Angel One authentication successful")
            return True

        except httpx.TimeoutException as e:
            logger.error(
                "Angel One authenticate timeout: path=%s error_type=%s",
                path, type(e).__name__,
            )
            raise AngelOneNetworkError(f"Connection timeout during authentication: {type(e).__name__}")
        except httpx.ConnectError as e:
            logger.error(
                "Angel One authenticate connect error: path=%s error_type=%s",
                path, type(e).__name__,
            )
            raise AngelOneNetworkError(f"DNS/connection failure during authentication: {type(e).__name__}")
        except httpx.RequestError as e:
            logger.error(
                "Angel One authenticate network error: path=%s error_type=%s",
                path, type(e).__name__,
            )
            raise AngelOneNetworkError(f"Network error during authentication: {type(e).__name__}")
        except AngelOneException:
            raise
        except Exception as e:
            logger.error("Unexpected error during Angel One authentication: %s", type(e).__name__)
            raise AngelOneAuthenticationError(f"Auth failed unexpectedly: {type(e).__name__}")

    # -----------------------------------------------------------------------
    # Read-only data methods
    # -----------------------------------------------------------------------

    def get_profile(self) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/rest/secure/angelbroking/user/v1/getProfile"
        return self._get(url)

    def get_rms(self) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/rest/secure/angelbroking/user/v1/getRMS"
        return self._get(url)

    def get_holdings(self) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/rest/secure/angelbroking/portfolio/v1/getHolding"
        return self._get(url)

    def get_positions(self) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/rest/secure/angelbroking/order/v1/getPosition"
        return self._get(url)

    def get_order_book(self) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/rest/secure/angelbroking/order/v1/getOrderBook"
        return self._get(url)

    def _get(self, url: str) -> Dict[str, Any]:
        path = _safe_path(url)

        if not self.auth.is_authenticated():
            logger.debug("No active session; authenticating before GET %s", path)
            self.authenticate()

        logger.debug("Angel One API request: method=GET path=%s", path)
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers=self.auth.get_auth_headers())
            return self._handle_response(response, path)

        except httpx.TimeoutException as e:
            logger.error(
                "Angel One GET timeout: path=%s error_type=%s",
                path, type(e).__name__,
            )
            raise AngelOneNetworkError(f"Request timeout on {path}: {type(e).__name__}")
        except httpx.ConnectError as e:
            logger.error(
                "Angel One GET connect error: path=%s error_type=%s host=%s",
                path, type(e).__name__, self.BASE_URL,
            )
            raise AngelOneNetworkError(
                f"DNS/connection failure reaching {self.BASE_URL}{path}: {type(e).__name__}"
            )
        except httpx.RequestError as e:
            logger.error(
                "Angel One GET network error: path=%s error_type=%s",
                path, type(e).__name__,
            )
            raise AngelOneNetworkError(f"Network error on {path}: {type(e).__name__}")
        except AngelOneException:
            # Already classified — let it propagate without re-wrapping
            raise

    # -----------------------------------------------------------------------
    # Execution guard — always blocked (READ-ONLY phase)
    # -----------------------------------------------------------------------

    def place_order(self, *args, **kwargs):
        """CRITICAL: Block any real order execution."""
        LiveBrokerExecutionGuard.verify_execution_allowed()
        raise NotImplementedError("Live execution is intentionally not implemented.")

    def modify_order(self, *args, **kwargs):
        LiveBrokerExecutionGuard.verify_execution_allowed()
        raise NotImplementedError("Live execution is intentionally not implemented.")

    def cancel_order(self, *args, **kwargs):
        LiveBrokerExecutionGuard.verify_execution_allowed()
        raise NotImplementedError("Live execution is intentionally not implemented.")
