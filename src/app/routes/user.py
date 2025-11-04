from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import UserCreate, UserResponse
from ..routes.auth import hash_password

DbSession = Annotated[Session, Depends(get_db)]
router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=List[UserResponse])
def get_users(db: DbSession):
    users = db.execute(select(User).order_by(User.id)).scalars().all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: DbSession):
    user = db.execute(select(User).where(
        User.id == user_id)).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@router.post("/", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, db: DbSession):
    existing_user = db.execute(select(User).where(
        User.email == user.email)).scalar_one_or_none()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email ya registrado")

    db_user = User(email=user.email,
                   hashed_password=hash_password(user.password))
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: DbSession):
    user = db.execute(select(User).where(
        User.id == user_id)).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    db.delete(user)
    db.commit()
    return None


@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_update: UserCreate, db: DbSession):
    user = db.execute(select(User).where(
        User.id == user_id)).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.email = user_update.email
    user.hashed_password = hash_password(user_update.password)
    db.commit()
    db.refresh(user)
    return user
