import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_active_user
from ..schemas import UserCreate, UserResponse
from ..services.auth_service import hash_password
from ..services.user_service import (
    delete_user,
    get_all_users,
    get_user_by_id,
    update_user,
    user_to_response,
)

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[UserResponse, Depends(get_current_active_user)]
router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserResponse])
def get_users(db: DbSession, current_user: CurrentUser) -> list[UserResponse]:
    users = get_all_users(db)
    return [user_to_response(user) for user in users]


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: uuid.UUID, db: DbSession, current_user: CurrentUser
) -> UserResponse:
    user = get_user_by_id(db, user_id)
    return user_to_response(user)


@router.delete("/{user_id}", status_code=204)
def delete_user_endpoint(
    user_id: uuid.UUID, db: DbSession, current_user: CurrentUser
) -> None:
    delete_user(db, user_id)
    return None


@router.put("/{user_id}", response_model=UserResponse)
def update_user_endpoint(
    user_id: uuid.UUID,
    user_update: UserCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> UserResponse:
    hashed_pwd = hash_password(user_update.password)
    user = update_user(
        db,
        user_id=user_id,
        email=user_update.email,
        username=user_update.username,
        hashed_password=hashed_pwd,
    )
    return user_to_response(user)
