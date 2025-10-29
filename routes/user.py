from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Annotated
from fastapi import Depends

import db_models
from schemas import UserCreate, UserResponse
from db import get_db


DbSession = Annotated[Session, Depends(get_db)]
router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=List[UserResponse])
def get_users(db: DbSession):
    users = db.execute(select(db_models.User)).scalars().all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: DbSession):
    user = db.execute(
        select(db_models.User).where(db_models.User.id == user_id)
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@router.post("/", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, db: DbSession):
    existing_user = db.execute(
        select(db_models.User).where(db_models.User.mail == user.mail)
    ).scalar_one_or_none()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email ya registrado")

    db_user = db_models.User(name=user.name, mail=user.mail)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: DbSession):
    user = db.execute(
        select(db_models.User).where(db_models.User.id == user_id)
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    db.delete(user)
    db.commit()
    return None
