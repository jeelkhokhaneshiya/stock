from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User
from app.schemas.token import TokenPayload
import logging

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"/api/v1/auth/login"
)

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error("Database session error (details hidden for security)")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again shortly.",
        )
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == token_data.sub).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def get_broker(db: Session, account_id: int):
    if settings.TRADING_MODE == "paper":
        from app.services.paper_broker import PaperBroker
        return PaperBroker(db, account_id)
    raise NotImplementedError(f"Broker for mode {settings.TRADING_MODE} not implemented")


import threading
from datetime import datetime, timedelta

_broker_lock = threading.Lock()
_global_angel_one_auth = None
_global_angel_one_client = None
_token_expiry = None

def get_angel_one_client():
    """
    Dependency factory: builds and returns a read-only AngelOneClient.
    Uses a singleton client with a threading lock to prevent authentication storms.
    """
    global _global_angel_one_auth, _global_angel_one_client, _token_expiry
    
    from app.services.brokers.angel_one.auth import AngelOneAuth
    from app.services.brokers.angel_one.client import AngelOneClient
    from app.services.brokers.angel_one.exceptions import (
        AngelOneAuthenticationError,
        AngelOneNetworkError,
        AngelOneRateLimitError,
        AngelOneInvalidResponseError,
    )

    required = {
        "ANGEL_ONE_API_KEY": settings.ANGEL_ONE_API_KEY,
        "ANGEL_ONE_CLIENT_ID": settings.ANGEL_ONE_CLIENT_ID,
        "ANGEL_ONE_PASSWORD": settings.ANGEL_ONE_PASSWORD,
        "ANGEL_ONE_TOTP_SECRET": settings.ANGEL_ONE_TOTP_SECRET,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Broker credentials not configured: {', '.join(missing)}",
        )

    with _broker_lock:
        if _global_angel_one_auth is None:
            _global_angel_one_auth = AngelOneAuth(
                api_key=settings.ANGEL_ONE_API_KEY,
                client_id=settings.ANGEL_ONE_CLIENT_ID,
                password=settings.ANGEL_ONE_PASSWORD,
                totp_secret=settings.ANGEL_ONE_TOTP_SECRET,
            )
            _global_angel_one_client = AngelOneClient(_global_angel_one_auth)

        # Authenticate if no token or token might be expired (e.g. 1 hour)
        needs_auth = not _global_angel_one_auth.is_authenticated()
        if not needs_auth and _token_expiry and datetime.utcnow() > _token_expiry:
            needs_auth = True

        if needs_auth:
            try:
                _global_angel_one_client.authenticate()
                _token_expiry = datetime.utcnow() + timedelta(hours=1) # Angel One token valid for ~2 hours typically
            except AngelOneAuthenticationError:
                logger.warning("Broker authentication failed in dependency factory")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Broker authentication failed. Verify credentials.",
                )
            except AngelOneRateLimitError:
                logger.warning("Broker rate-limited during authentication")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Angel One API rate limit reached. Retry after a short wait.",
                )
            except AngelOneNetworkError as e:
                logger.error("Broker network error during authentication: %s", type(e).__name__)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Cannot reach Angel One API. Check network connectivity.",
                )
            except AngelOneInvalidResponseError:
                logger.error("Broker returned unexpected response during authentication")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Angel One returned an unexpected response. Try again shortly.",
                )
            except Exception:
                logger.exception("Unexpected error in Angel One dependency factory")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Unexpected error during broker authentication.",
                )

    return _global_angel_one_client

def get_angel_one_data_service():
    """
    Dependency factory: returns a read-only AngelOneDataService.
    """
    from app.services.brokers.angel_one.data_service import AngelOneDataService
    client = get_angel_one_client()
    return AngelOneDataService(client)
