import logging
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .schemas import UserResponse
from .services.auth_service import decode_access_token
from .services.user_service import get_user_by_email, user_to_response
from .utils.custom_exceptions import (
    InvalidTokenException,
    UserNotFoundException,
)

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(scheme_name="BearerAuth", auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
        db: DbSession,
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> UserResponse:
    logger.info("Starting get_current_user")

    if not credentials or not hasattr(credentials, "credentials"):
        logger.error("No credentials provided")
        raise InvalidTokenException(detail="Missing credentials")

    token = credentials.credentials
    if not token:
        logger.error("Empty token provided")
        raise InvalidTokenException(detail="Empty token")

    logger.info(f"Token received: {token[:10]}...")

    payload = decode_access_token(token)
    logger.info("Token decoded successfully")

    email = payload.sub
    if not email:
        logger.error("No email in token payload")
        raise InvalidTokenException(detail="Invalid token payload")

    logger.info(f"Looking for user with email: {email}")

    user = get_user_by_email(db, email)

    if not user:
        logger.error(f"User not found for email: {email}")
        raise UserNotFoundException()

    logger.info(f"User found: {user.email}")

    return user_to_response(user)


def get_current_active_user(
        current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> UserResponse:
    # if not current_user.is_active:
    #     raise InactiveUserException()
    return current_user
