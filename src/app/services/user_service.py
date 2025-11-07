import uuid
from typing import Sequence

from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import User
from ..schemas import UserResponse
from ..utils.custom_exceptions import (
    ResourceNotFoundException,
    DuplicateResourceException,
)


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User:
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        raise ResourceNotFoundException(resource="User")
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


def get_all_users(db: Session) -> Sequence[User]:
    return db.execute(select(User).order_by(User.id)).scalars().all()


def create_user(db: Session, email: str, hashed_password: str) -> User:
    existing_user = get_user_by_email(db, email)
    if existing_user:
        raise DuplicateResourceException(detail="Email already registered")

    new_user = User(email=email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def update_user(
    db: Session, user_id: uuid.UUID, email: EmailStr, hashed_password: str
) -> User:
    user = get_user_by_id(db, user_id)

    if user.email != email:
        existing_user = get_user_by_email(db, email)
        if existing_user:
            raise DuplicateResourceException(detail="Email already in use")

    user.email = email
    user.hashed_password = hashed_password
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: uuid.UUID) -> None:
    user = get_user_by_id(db, user_id)
    db.delete(user)
    db.commit()


def user_to_response(user: User) -> UserResponse:
    return UserResponse(id=uuid.UUID(str(user.id)), email=user.email)
