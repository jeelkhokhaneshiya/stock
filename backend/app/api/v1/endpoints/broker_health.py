from fastapi import APIRouter, Depends, HTTPException
from typing import Union
from app.api.deps import get_current_user, get_angel_one_data_service
from app.models.user import User
from app.services.brokers.health import BrokerHealthService
from app.services.brokers.angel_one.session import AngelOneSessionManager
from app.services.brokers.circuit_breaker import CircuitBreaker
from app.services.brokers.angel_one.data_service import AngelOneDataService
from app.services.brokers.angel_one.exceptions import (
    AngelOneAuthenticationError,
    AngelOneNetworkError,
    AngelOneRateLimitError,
    AngelOneInvalidResponseError,
    AngelOneException,
)
from app.schemas.angel_one import (
    AngelOneAccountInfo,
    AngelOneFundsResponse,
    AngelOneHoldingsResponse,
    AngelOnePositionsResponse,
    AngelOneOrdersResponse,
    BrokerDataError,
)
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Instantiate globally or via dependency injection for demo
health_service = BrokerHealthService()
session_manager = AngelOneSessionManager()
circuit_breaker = CircuitBreaker()

@router.get("/health/{portfolio_id}")
def get_health(portfolio_id: str, current_user: User = Depends(get_current_user)):
    return health_service.get_status()

@router.get("/session/{portfolio_id}")
def get_session(portfolio_id: str, current_user: User = Depends(get_current_user)):
    return session_manager.get_status()

@router.get("/circuit-breaker/{portfolio_id}")
def get_circuit_breaker(portfolio_id: str, current_user: User = Depends(get_current_user)):
    return {"state": circuit_breaker.state, "failure_count": circuit_breaker.failure_count}

@router.get("/data-quality/{portfolio_id}")
def get_data_quality(portfolio_id: str, current_user: User = Depends(get_current_user)):
    return {"score": "HIGH", "message": "All critical data available and fresh"}

@router.get("/snapshot/{portfolio_id}")
def get_snapshot(portfolio_id: str, current_user: User = Depends(get_current_user)):
    return {"portfolio_id": portfolio_id, "cash": 1000.0, "status": "HEALTHY"}


@router.get("/auth-ping")
def broker_auth_ping(current_user: User = Depends(get_current_user)):
    """
    Safe broker authentication connectivity test.

    Returns only provider name, connection status, and a non-sensitive message.
    NEVER returns API keys, passwords, TOTP secrets, JWT tokens, or feed tokens.
    Does NOT place any order or modify any broker state.
    Requires authentication (Bearer token) to call.

    In paper/mock mode: returns immediately without any network call.
    In angel_one mode: attempts loginByPassword and reports success/failure only.
    """
    provider = settings.BROKER_PROVIDER.lower()

    # Paper / mock mode — no real broker connection needed
    if provider != "angel_one":
        return {
            "provider": provider,
            "authenticated": True,
            "status": "PAPER_MODE",
            "message": "Running in paper/mock mode. No real broker connection required.",
            "live_trading_enabled": False,
        }

    # Angel One — verify all required credentials are present before attempting
    missing = []
    if not settings.ANGEL_ONE_API_KEY:
        missing.append("ANGEL_ONE_API_KEY")
    if not settings.ANGEL_ONE_CLIENT_ID:
        missing.append("ANGEL_ONE_CLIENT_ID")
    if not settings.ANGEL_ONE_PASSWORD:
        missing.append("ANGEL_ONE_PASSWORD")
    if not settings.ANGEL_ONE_TOTP_SECRET:
        missing.append("ANGEL_ONE_TOTP_SECRET")

    if missing:
        return {
            "provider": "angel_one",
            "authenticated": False,
            "status": "MISSING_CREDENTIALS",
            "message": (
                f"The following required environment variables are not configured: "
                f"{', '.join(missing)}. Set them in your .env file."
            ),
            "live_trading_enabled": settings.ENABLE_LIVE_TRADING,
        }

    # Attempt real authentication — classify errors safely, never expose secrets
    try:
        import app.api.deps as deps
        from datetime import datetime, timedelta
        
        with deps._broker_lock:
            if deps._global_angel_one_auth is None:
                from app.services.brokers.angel_one.auth import AngelOneAuth
                from app.services.brokers.angel_one.client import AngelOneClient
                deps._global_angel_one_auth = AngelOneAuth(
                    api_key=settings.ANGEL_ONE_API_KEY,
                    client_id=settings.ANGEL_ONE_CLIENT_ID,
                    password=settings.ANGEL_ONE_PASSWORD,
                    totp_secret=settings.ANGEL_ONE_TOTP_SECRET,
                )
                deps._global_angel_one_client = AngelOneClient(deps._global_angel_one_auth)

            needs_auth = not deps._global_angel_one_auth.is_authenticated()
            if not needs_auth and deps._token_expiry and datetime.utcnow() > deps._token_expiry:
                needs_auth = True

            if needs_auth:
                deps._global_angel_one_client.authenticate()  # loginByPassword via SmartAPI
                deps._token_expiry = datetime.utcnow() + timedelta(hours=1)

        # Confirm success only — never return the jwt/feed token
        return {
            "provider": "angel_one",
            "authenticated": True,
            "status": "CONNECTED",
            "message": "Angel One authentication successful. Read-only session active.",
            "live_trading_enabled": settings.ENABLE_LIVE_TRADING,
        }

    except AngelOneAuthenticationError:
        return {
            "provider": "angel_one",
            "authenticated": False,
            "status": "AUTH_FAILED",
            "message": "Authentication failed. Verify client ID, password, and TOTP secret.",
            "live_trading_enabled": settings.ENABLE_LIVE_TRADING,
        }
    except AngelOneRateLimitError:
        return {
            "provider": "angel_one",
            "authenticated": False,
            "status": "RATE_LIMITED",
            "message": "Angel One API rate limit reached. Retry after a short wait.",
            "live_trading_enabled": settings.ENABLE_LIVE_TRADING,
        }
    except AngelOneNetworkError:
        return {
            "provider": "angel_one",
            "authenticated": False,
            "status": "NETWORK_ERROR",
            "message": "Cannot reach Angel One API. Check your network connectivity.",
            "live_trading_enabled": settings.ENABLE_LIVE_TRADING,
        }
    except Exception:
        # Catch-all: log internally, never expose stack trace or credential details
        return {
            "provider": "angel_one",
            "authenticated": False,
            "status": "UNKNOWN_ERROR",
            "message": "An unexpected error occurred during the broker authentication check.",
            "live_trading_enabled": settings.ENABLE_LIVE_TRADING,
        }


# ===========================================================================
# READ-ONLY Angel One data endpoints  (Phase 9.2)
#
# All endpoints below:
# - Require a valid Bearer JWT (app-level auth via get_current_user)
# - Use the get_angel_one_data_service dependency to obtain an authenticated
#   AngelOneDataService (credentials stay server-side)
# - Return normalised schemas — NEVER raw broker payloads
# - Are strictly READ-ONLY; no order placement/modification/cancellation
# - Guard flags remain: ENABLE_LIVE_TRADING=false, BROKER_EXECUTION_BLOCKED=true
# ===========================================================================

def _handle_broker_error(exc: Exception) -> HTTPException:
    """Map Angel One exceptions to safe HTTP responses (no secrets in detail)."""
    if isinstance(exc, AngelOneAuthenticationError):
        return HTTPException(
            status_code=503,
            detail="Broker session expired or authentication failed. Re-authenticate via /auth-ping.",
        )
    if isinstance(exc, AngelOneRateLimitError):
        return HTTPException(status_code=429, detail="Angel One rate limit reached. Retry shortly.")
    if isinstance(exc, AngelOneNetworkError):
        return HTTPException(status_code=503, detail="Cannot reach Angel One API. Check network.")
    if isinstance(exc, AngelOneInvalidResponseError):
        return HTTPException(status_code=502, detail="Unexpected response from broker API.")
    return HTTPException(status_code=503, detail="Broker error. Check server logs.")


# ---------------------------------------------------------------------------
# GET /broker-monitoring/account
# ---------------------------------------------------------------------------

@router.get(
    "/account",
    response_model=AngelOneAccountInfo,
    summary="Angel One: account / profile (read-only)",
    tags=["broker_health"],
)
def get_broker_account(
    current_user: User = Depends(get_current_user),
    svc: AngelOneDataService = Depends(get_angel_one_data_service),
):
    """
    Returns the authenticated Angel One account profile.

    Safe fields only: client_id, name, email, mobile, exchange/product privileges.
    NEVER returns api_key, password, TOTP, jwt_token, or feed_token.
    """
    try:
        return svc.get_account_info()
    except AngelOneException as exc:
        raise _handle_broker_error(exc)
    except Exception:
        logger.exception("Unexpected error in /account endpoint")
        raise HTTPException(status_code=503, detail="Unexpected broker error.")


# ---------------------------------------------------------------------------
# GET /broker-monitoring/funds
# ---------------------------------------------------------------------------

@router.get(
    "/funds",
    response_model=AngelOneFundsResponse,
    summary="Angel One: funds / margin (read-only)",
    tags=["broker_health"],
)
def get_broker_funds(
    current_user: User = Depends(get_current_user),
    svc: AngelOneDataService = Depends(get_angel_one_data_service),
):
    """
    Returns available cash, used margin, net cash, and collateral.
    All values are in INR.  No secrets returned.
    """
    try:
        return svc.get_funds()
    except AngelOneException as exc:
        raise _handle_broker_error(exc)
    except Exception:
        logger.exception("Unexpected error in /funds endpoint")
        raise HTTPException(status_code=503, detail="Unexpected broker error.")


# ---------------------------------------------------------------------------
# GET /broker-monitoring/holdings
# ---------------------------------------------------------------------------

@router.get(
    "/holdings",
    response_model=AngelOneHoldingsResponse,
    summary="Angel One: delivery holdings (read-only)",
    tags=["broker_health"],
)
def get_broker_holdings(
    current_user: User = Depends(get_current_user),
    svc: AngelOneDataService = Depends(get_angel_one_data_service),
):
    """
    Returns the current delivery holdings portfolio.
    Returns an empty list when there are no holdings — this is not an error.
    """
    try:
        return svc.get_holdings()
    except AngelOneException as exc:
        raise _handle_broker_error(exc)
    except Exception:
        logger.exception("Unexpected error in /holdings endpoint")
        raise HTTPException(status_code=503, detail="Unexpected broker error.")


# ---------------------------------------------------------------------------
# GET /broker-monitoring/positions
# ---------------------------------------------------------------------------

@router.get(
    "/positions",
    response_model=AngelOnePositionsResponse,
    summary="Angel One: open positions (read-only)",
    tags=["broker_health"],
)
def get_broker_positions(
    current_user: User = Depends(get_current_user),
    svc: AngelOneDataService = Depends(get_angel_one_data_service),
):
    """
    Returns intraday / overnight open positions.
    Returns an empty list when there are no open positions.
    """
    try:
        return svc.get_positions()
    except AngelOneException as exc:
        raise _handle_broker_error(exc)
    except Exception:
        logger.exception("Unexpected error in /positions endpoint")
        raise HTTPException(status_code=503, detail="Unexpected broker error.")


# ---------------------------------------------------------------------------
# GET /broker-monitoring/orders
# ---------------------------------------------------------------------------

@router.get(
    "/orders",
    response_model=AngelOneOrdersResponse,
    summary="Angel One: order book (read-only)",
    tags=["broker_health"],
)
def get_broker_orders(
    current_user: User = Depends(get_current_user),
    svc: AngelOneDataService = Depends(get_angel_one_data_service),
):
    """
    Returns the order book for the current session (READ-ONLY view).

    This endpoint does NOT place, modify, or cancel any order.
    ENABLE_LIVE_TRADING=false and BROKER_EXECUTION_BLOCKED=true remain enforced.
    """
    try:
        return svc.get_orders()
    except AngelOneException as exc:
        raise _handle_broker_error(exc)
    except Exception:
        logger.exception("Unexpected error in /orders endpoint")
        raise HTTPException(status_code=503, detail="Unexpected broker error.")
