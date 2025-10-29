from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Column[int] = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    mail = Column(String(255), unique=True, nullable=False, index=True)
