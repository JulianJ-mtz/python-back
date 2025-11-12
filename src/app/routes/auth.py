import logging
from typing import Annotated

from fastapi import APIRouter, status
from fastapi.params import Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_active_user
from ..schemas import (
    Token,
    TokenRefresh,
    UserLogin,
    UserRegister,
    UserResponse,
)
from ..services.auth_service import (
    authenticate_user,
    create_token_pair,
    decode_refresh_token,
    hash_password,
)
from ..services.user_service import (
    create_user,
    get_user_by_email,
)
from ..utils.custom_exceptions import (
    InvalidTokenException,
    UserNotFoundException,
)

router = APIRouter(prefix="/auth", tags=["auth"])
DbSession = Annotated[Session, Depends(get_db)]
logger = logging.getLogger(__name__)


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: DbSession) -> Token:
    hashed_pwd = hash_password(user_data.password)
    user = create_user(
        db,
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_pwd,
    )
    return create_token_pair(user.email)


@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: DbSession) -> Token:
    email = authenticate_user(db, user_data.email, user_data.password)
    return create_token_pair(email)


@router.post("/refresh", response_model=Token)
def refresh_token(token_data: TokenRefresh, db: DbSession) -> Token:
    payload = decode_refresh_token(token_data.refresh_token)
    email = payload.sub
    if not email:
        raise InvalidTokenException(detail="Invalid token payload")

    user = get_user_by_email(db, email)
    if not user:
        raise UserNotFoundException()

    return create_token_pair(user.email)


@router.get("/me", response_model=UserResponse)
def read_current_user(
    current_user: Annotated[UserResponse, Depends(get_current_active_user)],
) -> UserResponse:
    return current_user
