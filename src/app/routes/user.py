from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import UserCreate, UserResponse
from ..routes.auth import hash_password
from ..utils.custom_exceptions import ResourceNotFoundException, DuplicateResourceException

DbSession = Annotated[Session, Depends(get_db)]
router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserResponse])
def get_users(db: DbSession):
    users = db.execute(select(User).order_by(User.id)).scalars().all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: uuid.UUID, db: DbSession):
    user = db.execute(select(User).where(
        User.id == user_id)
    ).scalar_one_or_none()

    if not user:
        raise ResourceNotFoundException(resource="User")
    
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: uuid.UUID, db: DbSession):
    user = db.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()

    if not user:
        raise ResourceNotFoundException(resource="User")

    db.delete(user)
    db.commit()
    return None


@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: uuid.UUID, user_update: UserCreate, db: DbSession):
    user = db.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()

    if not user:
        raise ResourceNotFoundException(resource="User")

    # Check if email is already taken by another user
    if user.email != user_update.email:
        existing_user = db.execute(
            select(User).where(User.email == user_update.email)
        ).scalar_one_or_none()
        
        if existing_user:
            raise DuplicateResourceException(detail="Email already in use")

    user.email = user_update.email
    user.hashed_password = hash_password(user_update.password)
    db.commit()
    db.refresh(user)
    return user
