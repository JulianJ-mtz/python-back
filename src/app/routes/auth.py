import os
from datetime import datetime, timedelta
import logging

import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, status
from fastapi.params import Depends
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.util.typing import Annotated

from ..database import get_db
from ..dependencies import get_current_active_user
from ..models import User
from ..schemas import Token, TokenRefresh, UserLogin, UserRegister, UserResponse
from ..utils.custom_exceptions import (
    TokenExpiredException,
    InvalidTokenException,
    UserNotFoundException,
    InvalidCredentialsException,
    DuplicateResourceException,
)

router = APIRouter(prefix="/auth", tags=["auth"])
DbSession = Annotated[Session, Depends(get_db)]
logger = logging.getLogger(__name__)

load_dotenv()

SECRET_KEY_ENV = os.getenv("SECRET_KEY")
ALGORITHM_ENV = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES_ENV = float(os.getenv("MINUTES_TOKEN_EXPIRE", 60))
REFRESH_TOKEN_EXPIRE_DAYS_ENV = float(os.getenv("DAYS_REFRESH_TOKEN_EXPIRE", 7))

if not SECRET_KEY_ENV:
    raise ValueError("SECRET_KEY environment variable is not set")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    now = datetime.now()
    expire = (
        now + expires_delta
        if expires_delta
        else now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES_ENV)
    )
    payload = {
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "sub": str(subject),
        "type": "access",
    }
    return jwt.encode(payload, SECRET_KEY_ENV, algorithm=ALGORITHM_ENV)


def create_refresh_token(subject: str, expires_delta: timedelta | None = None) -> str:
    now = datetime.now()
    expire = (
        now + expires_delta
        if expires_delta
        else now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS_ENV)
    )
    payload = {
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "sub": str(subject),
        "type": "refresh",
    }
    return jwt.encode(payload, SECRET_KEY_ENV, algorithm=ALGORITHM_ENV)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY_ENV, algorithms=ALGORITHM_ENV)
        if payload.get("type") != "access":
            raise InvalidTokenException(detail="Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenExpiredException()
    except jwt.InvalidTokenError:
        raise InvalidTokenException()


def decode_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY_ENV, algorithms=ALGORITHM_ENV)
        if payload.get("type") != "refresh":
            raise InvalidTokenException(detail="Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenExpiredException()
    except jwt.InvalidTokenError:
        raise InvalidTokenException(detail="Invalid refresh token")


async def get_current_user(
        db: DbSession,
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> User:
    """Get the current user from the token.

    This function is used by the auth middleware to validate the token
    and get the user from the database.

    Args:
        db: Database session
        credentials: HTTP Authorization credentials containing the JWT token

    Returns:
        User: The authenticated user

    Raises:
        AuthenticationException: If the token is invalid or the user is not found
    """
    logger.info("Starting get_current_user")

    if not credentials or not hasattr(credentials, "credentials"):
        logger.error("No credentials provided")
        raise InvalidTokenException(detail="Missing credentials")

    token = credentials.credentials
    if not token:
        logger.error("Empty token provided")
        raise InvalidTokenException(detail="Empty token")

    logger.info(f"Token received: {token[:10]}...")

    # Decode token (will raise appropriate exceptions if invalid)
    payload = decode_access_token(token)
    logger.info("Token decoded successfully")

    email = payload.get("sub")
    if not email:
        logger.error("No email in token payload")
        raise InvalidTokenException(detail="Invalid token payload")

    logger.info(f"Looking for user with email: {email}")

    user = db.execute(
        select(User).where(User.email == email)
    ).scalar_one_or_none()

    if not user:
        logger.error(f"User not found for email: {email}")
        raise UserNotFoundException()

    logger.info(f"User found: {user.email}")
    return user


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user: UserRegister, db: DbSession):
    existing_user = db.execute(
        select(User).where(User.email == user.email)
    ).scalar_one_or_none()

    if existing_user:
        raise DuplicateResourceException(detail="Email already registered")

    register_user = User(
        email=user.email,
        hashed_password=hash_password(user.password)
    )

    db.add(register_user)
    db.commit()
    db.refresh(register_user)

    access_token = create_access_token(subject=register_user.email)
    refresh_token = create_refresh_token(subject=register_user.email)

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: DbSession):
    user = db.execute(
        select(User).where(User.email == user_data.email)
    ).scalar_one_or_none()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise InvalidCredentialsException()

    access_token = create_access_token(subject=user.email)
    refresh_token = create_refresh_token(subject=user.email)

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
def refresh_token(token_data: TokenRefresh, db: DbSession):
    payload = decode_refresh_token(token_data.refresh_token)
    email = payload.get("sub")

    if not email:
        raise InvalidTokenException(detail="Invalid token payload")

    user = db.execute(
        select(User).where(User.email == email)
    ).scalar_one_or_none()

    if not user:
        raise UserNotFoundException()

    access_token = create_access_token(subject=email)
    refresh_token = create_refresh_token(subject=email)

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserResponse)
def read_current_user(
        current_user: Annotated[User, Depends(get_current_active_user)],
):
    return current_user