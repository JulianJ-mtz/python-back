import uuid
from typing import TYPE_CHECKING
from datetime import datetime
from enum import Enum

from sqlalchemy import UUID, ForeignKey, Integer, Float, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User


class TestMode(str, Enum):
    TIME = "time"
    CLICKS = "clicks"


VALID_MODE_VALUES = {
    TestMode.TIME: {15, 30, 60, 120},
    TestMode.CLICKS: {25, 50, 100, 200},
}


class Score(Base):
    __tablename__: str = "scores"

    id: Mapped[UUID[str]] = mapped_column(
        UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4
    )

    user_id: Mapped[UUID[str]] = mapped_column(ForeignKey("users.id"))

    mode: Mapped[str] = mapped_column(String(10), nullable=False)
    mode_value: Mapped[int] = mapped_column(Integer, nullable=False)

    cps: Mapped[float] = mapped_column(Float, nullable=False)
    total_clicks: Mapped[int] = mapped_column(Integer, nullable=False)
    correct_clicks: Mapped[int] = mapped_column(Integer, nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)
    accuracy: Mapped[float] = mapped_column(Float, nullable=False)
    consistency: Mapped[float] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="scores")
