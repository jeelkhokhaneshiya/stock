from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi.security import OAuth2PasswordRequestForm
from app.api import deps
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.schemas.token import Token
from app.core.security import verify_password, get_password_hash, create_access_token
from typing import Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(deps.get_db)) -> Any:
    try:
        existing = db.query(User).filter(User.email == user_in.email).first()
    except SQLAlchemyError:
        logger.error("Database error during registration lookup")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again shortly.",
        )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists.",
        )

    hashed_password = get_password_hash(user_in.password)
    db_user = User(
        email=user_in.email,
        password_hash=hashed_password,
    )
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    except SQLAlchemyError:
        db.rollback()
        logger.error("Database error during user registration")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again shortly.",
        )

    return db_user


@router.post("/login", response_model=Token)
def login(
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    # Attempt to load the user — catch DB errors explicitly
    try:
        user = db.query(User).filter(User.email == form_data.username).first()
    except SQLAlchemyError:
        logger.error("Database error during login user lookup")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again shortly.",
        )

    # Wrong email or wrong password → 401 (not 400, per OAuth2/RFC 6749)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is deactivated.",
        )

    access_token = create_access_token(user.id)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(deps.get_current_user)) -> Any:
    return current_user
