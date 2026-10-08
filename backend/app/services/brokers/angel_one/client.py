import httpx
import logging
import json
import threading
import time
from typing import Dict, Any, Optional

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
    # -----------------------------------------------------------------------
    BASE_URL = "https://apiconnect.angelone.in"

    # -----------------------------------------------------------------------
    # Auth storm prevention:
    # Angel One enforces one active session per client_id at a time.
    # Re-authenticating invalidates the previous JWT, causing a cascade of
    # 403s in concurrent or rapid-sequential callers.
    #
    # Rules:
    #   - Authenticate once; reuse the JWT for all subsequent calls.
    #   - On genuine session expiry (403/AB1004/etc.), re-auth ONCE only.
    #   - Never attempt re-auth within AUTH_COOLDOWN_SECONDS of the last attempt.
    #   - A single threading.Lock serialises auth across threads.
    # -----------------------------------------------------------------------
    AUTH_COOLDOWN_SECONDS = 30  # minimum gap between login attempts

    def __init__(self, auth: AngelOneAuth):
        self.auth = auth
        self.timeout = httpx.Timeout(15.0, connect=8.0)
        limits = httpx.Limits(max_keepalive_connections=50, max_connections=100)
        self.http_client = httpx.Client(timeout=self.timeout, limits=limits)

        # Per-instance auth lock and cooldown state
        self._auth_lock = threading.Lock()
        self._last_auth_attempt_ts: Optional[float] = None   # monotonic clock
        self._auth_attempt_count: int = 0

    def __del__(self):
        try:
            self.http_client.close()
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Response handling
    # -----------------------------------------------------------------------

    def _handle_response(self, response: httpx.Response, path: str = "") -> Dict[str, Any]:
        status = response.status_code
        logger.debug("Angel One API response: path=%s status=%d", path, status)

        if status == 429:
            logger.warning("Angel One rate limit hit: path=%s", path)
            raise AngelOneRateLimitError("Rate limit exceeded")

        if status in (401, 403):
            logger.warning("Angel One auth rejected: path=%s status=%d", path, status)
            if "historical/v1/getCandleData" in path:
                if "exceeding access rate" in response.text.lower():
                    logger.warning("Angel One rate limit hit (WAF 403): path=%s", path)
                    raise AngelOneRateLimitError("Rate limit exceeded (WAF 403)")
                raise AngelOneInvalidResponseError(f"Market data permissions denied: {status}")
            self.auth.clear_tokens()
            raise AngelOneAuthenticationError(f"Authentication rejected by broker: {status}")

        if status >= 500:
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
    # Authentication — single session management
    # -----------------------------------------------------------------------

    def authenticate(self) -> bool:
        """
        Authenticate using SmartAPI loginByPassword.

        Session contract
        ----------------
        - If already authenticated (jwt_token present), return True immediately.
        - If a re-auth was attempted within AUTH_COOLDOWN_SECONDS, raise
          AngelOneAuthenticationError rather than attempting again (auth storm
          prevention).  Angel One invalidates previous sessions on each login,
          so rapid re-auth cascades cause every existing caller to get 403.
        - Only one thread at a time may attempt authentication (threading.Lock).
        - Credentials/tokens are NEVER logged.
        """
        with self._auth_lock:
            # Already authenticated — reuse the session.
            if self.auth.is_authenticated():
                return True

            # Auth storm guard: enforce minimum cooldown between login attempts.
            now = time.monotonic()
            if self._last_auth_attempt_ts is not None:
                elapsed = now - self._last_auth_attempt_ts
                if elapsed < self.AUTH_COOLDOWN_SECONDS:
                    remaining = self.AUTH_COOLDOWN_SECONDS - elapsed
                    logger.warning(
                        "Angel One auth cooldown active: %.1fs remaining. "
                        "Not re-authenticating to prevent session invalidation storm.",
                        remaining,
                    )
                    raise AngelOneAuthenticationError(
                        f"Auth cooldown active: retry in {remaining:.0f}s "
                        f"(prevents session storm)"
                    )

            self._last_auth_attempt_ts = now
            self._auth_attempt_count += 1

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

            logger.info(
                "Angel One authenticate: attempt=%d path=%s",
                self._auth_attempt_count, path,
            )
            try:
                response = self.http_client.post(url, headers=headers, json=payload)
                data = self._handle_response(response, path)

                self.auth.set_tokens(
                    jwt_token=data.get("jwtToken"),
                    refresh_token=data.get("refreshToken"),
                    feed_token=data.get("feedToken"),
                )
                logger.info("Angel One authentication successful (attempt=%d)", self._auth_attempt_count)
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

    def get_candle_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/rest/secure/angelbroking/historical/v1/getCandleData"
        return self._post(url, payload)

    # -----------------------------------------------------------------------
    # Internal HTTP helpers — single-retry on genuine session expiry
    # -----------------------------------------------------------------------

    def _post(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", url, payload=payload)

    def _get(self, url: str) -> Dict[str, Any]:
        return self._request("GET", url)

    def _request(self, method: str, url: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a GET or POST against the Angel One API.

        Session-expiry handling
        -----------------------
        If the call returns a genuine session-expiry error (403 or AB1004/etc.)
        and the cooldown has elapsed, re-authenticate ONCE and retry.
        This is the only place re-auth is triggered after the initial login.
        We never retry more than once per call to prevent cascades.
        """
        path = _safe_path(url)

        # Ensure we have a session before the first call
        if not self.auth.is_authenticated():
            logger.debug("No active session; authenticating before %s %s", method, path)
            self.authenticate()

        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self._do_http(method, url, path, payload)
                return self._handle_response(response, path)
            except AngelOneRateLimitError:
                if attempt < max_retries - 1:
                    sleep_time = (attempt + 1) * 1.5
                    logger.warning("Rate limit hit on %s %s, retrying in %.1fs...", method, path, sleep_time)
                    time.sleep(sleep_time)
                else:
                    raise
            except AngelOneAuthenticationError:
                if attempt == 0:
                    # Genuine session expiry detected — attempt one re-auth then retry
                    logger.info(
                        "Session expired on %s %s; attempting single re-authentication.",
                        method, path,
                    )
                    self.authenticate()   # raises if cooldown blocks or credentials fail
                    # Let the loop retry
                else:
                    raise

    def _do_http(
        self,
        method: str,
        url: str,
        path: str,
        payload: Dict[str, Any] = None,
    ) -> httpx.Response:
        """Execute the raw HTTP request, mapping transport errors to AngelOneNetworkError."""
        logger.debug("Angel One API request: method=%s path=%s", method, path)
        try:
            if method == "GET":
                return self.http_client.get(url, headers=self.auth.get_auth_headers())
            elif method == "POST":
                return self.http_client.post(url, headers=self.auth.get_auth_headers(), json=payload)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

        except httpx.TimeoutException as e:
            logger.error("Angel One %s timeout: path=%s error_type=%s", method, path, type(e).__name__)
            raise AngelOneNetworkError(f"Request timeout on {path}: {type(e).__name__}")
        except httpx.ConnectError as e:
            logger.error(
                "Angel One %s connect error: path=%s error_type=%s host=%s",
                method, path, type(e).__name__, self.BASE_URL,
            )
            raise AngelOneNetworkError(
                f"DNS/connection failure reaching {self.BASE_URL}{path}: {type(e).__name__}"
            )
        except httpx.RequestError as e:
            logger.error("Angel One %s network error: path=%s error_type=%s", method, path, type(e).__name__)
            raise AngelOneNetworkError(f"Network error on {path}: {type(e).__name__}")
        except AngelOneException:
            raise

    # -----------------------------------------------------------------------
    # Execution guard — ALWAYS blocked (READ-ONLY phase)
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
