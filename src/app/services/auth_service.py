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
    TokenExpiredException,
)

logger = logging.getLogger(__name__)
load_dotenv()

SECRET_KEY_ENV = os.getenv("SECRET_KEY")
ALGORITHM_ENV = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES_ENV = float(os.getenv("MINUTES_TOKEN_EXPIRE", "60"))
REFRESH_TOKEN_EXPIRE_DAYS_ENV = float(os.getenv("DAYS_REFRESH_TOKEN_EXPIRE", "7"))

if not SECRET_KEY_ENV:
    raise ValueError("SECRET_KEY environment variable is not set")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Password utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña coincide con su hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(plain_password: str) -> str:
    """Genera un hash de una contraseña."""
    return pwd_context.hash(plain_password)


# Token utilities
def _create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    """Crea un token JWT."""
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


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Crea un access token."""
    delta = (
        expires_delta
        if expires_delta
        else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES_ENV)
    )
    return _create_token(subject, "access", delta)


def create_refresh_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Crea un refresh token."""
    delta = (
        expires_delta
        if expires_delta
        else timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS_ENV)
    )
    return _create_token(subject, "refresh", delta)


def _decode_token(token: str, expected_type: str) -> JWTPayload:
    """Decodifica y valida un token JWT."""
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
    """Crea un par de tokens (access y refresh) para un usuario."""
    access_token = create_access_token(subject=email)
    refresh_token = create_refresh_token(subject=email)
    return Token(access_token=access_token, refresh_token=refresh_token)


def authenticate_user(db: Session, email: str, password: str) -> str:
    """
    Autentica un usuario con email y contraseña.
    Retorna el email si es válido, lanza excepción si no.
    """
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsException()
    return user.email
