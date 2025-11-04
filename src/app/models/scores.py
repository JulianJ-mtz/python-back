from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

if TYPE_CHECKING:
    from .user import User

class Score(Base):
    __tablename__ = "scores"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    points: Mapped[float] = mapped_column(default=0.0)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    user: Mapped["User"] = relationship(back_populates="scores")