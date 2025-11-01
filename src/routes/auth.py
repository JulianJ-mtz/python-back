import os
from datetime import datetime, timedelta

import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, status
from fastapi.params import Depends
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.util.typing import Annotated

from ..schemas import Token, TokenRefresh, UserLogin, UserRegister, UserResponse
from .. import db_models
from ..db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])
DbSession = Annotated[Session, Depends(get_db)]

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
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def decode_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY_ENV, algorithms=ALGORITHM_ENV)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired. Please login again",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> db_models.User:
    token = credentials.credentials
    payload = decode_access_token(token)
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Token Payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.execute(
        select(db_models.User).where(db_models.User.mail == email)
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


@router.post("/register", response_model=Token, status_code=201)
def register(user: UserRegister, db: DbSession):
    existing_user = db.execute(
        select(db_models.User).where(db_models.User.mail == user.mail)
    ).scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    register_user = db_models.User(
        name=user.name, mail=user.mail, password=hash_password(user.password)
    )

    db.add(register_user)
    db.commit()
    db.refresh(register_user)

    access_token = create_access_token(subject=register_user.mail)
    refresh_token = create_refresh_token(subject=register_user.mail)

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: DbSession):
    user = db.execute(
        select(db_models.User).where(db_models.User.mail == user_data.mail)
    ).scalar_one_or_none()
    if not user or not verify_password(user_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=user.mail)
    refresh_token = create_refresh_token(subject=user.mail)
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
def refresh_token(token_data: TokenRefresh, db: DbSession):
    payload = decode_refresh_token(token_data.refresh_token)
    email = payload.get("sub")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.execute(
        select(db_models.User).where(db_models.User.mail == email)
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=email)
    refresh_token = create_refresh_token(subject=email)

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserResponse)
def read_current_user(
    current_user: Annotated[db_models.User, Depends(get_current_user)],
):
    return current_user
