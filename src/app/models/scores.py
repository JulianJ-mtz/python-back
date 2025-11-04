import uuid
from typing import TYPE_CHECKING

from sqlalchemy import UUID, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User


class Score(Base):
    __tablename__: str = "scores"

    id: Mapped[UUID[str]] = mapped_column(
        UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4
    )
    points: Mapped[float] = mapped_column(default=0.0)
    user_id: Mapped[UUID[str]] = mapped_column(ForeignKey("users.id"))

    user: Mapped["User"] = relationship(back_populates="scores")
