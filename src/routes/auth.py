import os

import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext

load_dotenv()

SECRET_KEY_ENV = os.getenv("SECRET_KEY")
ALGORITHM_ENV = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES_ENV = os.getenv("MINUTES_TOKEN_EXPIRE")


if not SECRET_KEY_ENV:
    raise ValueError("SECRET_KEY environment variable is not set")

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
