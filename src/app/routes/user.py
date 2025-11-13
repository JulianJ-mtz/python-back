import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_active_user
from ..schemas import UserResponse, UserUpdate
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
def get_users(
    db: DbSession,
    #    current_user: CurrentUser
) -> list[UserResponse]:
    users = get_all_users(db)
    return [user_to_response(user) for user in users]


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: uuid.UUID, db: DbSession) -> UserResponse:
    #    current_user: CurrentUser
    user = get_user_by_id(db, user_id)
    return user_to_response(user)


@router.delete("/{user_id}", status_code=204)
def delete_user_endpoint(user_id: uuid.UUID, db: DbSession) -> None:
    #    current_user: CurrentUser
    delete_user(db, user_id)
    return None


@router.put("/", response_model=UserResponse)
def update_user_endpoint(
    user_update: UserUpdate,
    db: DbSession,
    #    current_user: CurrentUser
) -> UserResponse:
    if user_update.password is not None:
        hashed_pwd = hash_password(user_update.password)
    else:
        hashed_pwd = None

    user = update_user(
        db,
        user_to_update=UserUpdate(
            id=user_update.id,
            email=user_update.email,
            username=user_update.username,
            password=hashed_pwd,
        ),
    )
    return user_to_response(user)
