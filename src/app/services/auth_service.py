import logging
import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from passlib.context import CryptContext
from pydantic import ValidationError
from sqlalchemy.orm import Session

from .user_service import get_user_by_email
from ..schemas import JWTPayload, Token
from ..utils.custom_exceptions import (
    InvalidCredentialsException,
    InvalidTokenException,
    PasswordTooLongException,
    TokenExpiredException,
)

logger = logging.getLogger(__name__)
load_dotenv()

SECRET_KEY_ENV = os.getenv("SECRET_KEY") or ""
ALGORITHM_ENV = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES_ENV = float(os.getenv("MINUTES_TOKEN_EXPIRE", "60"))
REFRESH_TOKEN_EXPIRE_DAYS_ENV = float(os.getenv("DAYS_REFRESH_TOKEN_EXPIRE", "7"))

if not SECRET_KEY_ENV:
    raise ValueError("SECRET_KEY environment variable is not set")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
BCRYPT_MAX_BYTES = 72


def _ensure_password_length(password: str) -> None:
    encoded = password.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_BYTES:
        logger.info("Password exceeds bcrypt byte limit", extra={"length": len(encoded)})
        raise PasswordTooLongException(max_bytes=BCRYPT_MAX_BYTES)


# Password utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies if a password matches its hash."""
    _ensure_password_length(plain_password)
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError as exc:
        logger.exception("Password verification failed unexpectedly")
        raise InvalidCredentialsException() from exc


def hash_password(plain_password: str) -> str:
    """Generates a hash for a password."""
    _ensure_password_length(plain_password)
    try:
        return pwd_context.hash(plain_password)
    except ValueError as exc:
        logger.exception("Password hashing failed unexpectedly")
        raise PasswordTooLongException(max_bytes=BCRYPT_MAX_BYTES) from exc


# Token utilities
def _create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    """Creates a JWT token."""
    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload: dict[str, int | str] = {
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "sub": str(subject),
        "type": token_type,
    }

    encoded: str = jwt.encode(payload, SECRET_KEY_ENV, algorithm=ALGORITHM_ENV)
    return encoded


def create_token(
    subject: str, token_type: str = "access", expires_delta: timedelta | None = None
) -> str:
    """Create a JWT token, either access or refresh."""
    if not expires_delta:
        if token_type == "access":
            expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES_ENV)
        elif token_type == "refresh":
            expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS_ENV)
        else:
            raise ValueError(f"Invalid token type: {token_type}")

    return _create_token(subject, token_type, expires_delta)


def _decode_token(token: str, expected_type: str) -> JWTPayload:
    """Decodes and validates a JWT token."""
    try:
        payload_dict = jwt.decode(token, SECRET_KEY_ENV, algorithms=[ALGORITHM_ENV])
        payload = JWTPayload.model_validate(payload_dict)

        if payload.type != expected_type:
            raise InvalidTokenException(detail="Invalid token type")

        return payload
    except jwt.ExpiredSignatureError:
        raise TokenExpiredException()
    except jwt.InvalidTokenError:
        raise InvalidTokenException()
    except ValidationError:
        raise InvalidTokenException(detail="Invalid token payload structure")


def decode_access_token(token: str) -> JWTPayload:
    return _decode_token(token, "access")


def decode_refresh_token(token: str) -> JWTPayload:
    return _decode_token(token, "refresh")


def create_token_pair(email: str) -> Token:
    access_token = create_token(subject=email, token_type="access")
    refresh_token = create_token(subject=email, token_type="refresh")
    return Token(access_token=access_token, refresh_token=refresh_token)


def authenticate_user(db: Session, email: str, password: str) -> str:
    """
    Authenticates a user with email and password.
    Returns the email if valid, raises exception if not.
    """
    _ensure_password_length(password)
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsException()
    return user.email
