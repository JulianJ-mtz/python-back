from typing import Annotated

from fastapi import Depends
from fastapi.routing import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_active_user
from ..models import Score
from ..schemas import ScoreResponse, UserResponse

DbSession = Annotated[Session, Depends(get_db)]
router = APIRouter(prefix="/score", tags=["score"])


@router.get("/", response_model=list[ScoreResponse])
def get_scores(db: DbSession) -> list[ScoreResponse]:
    """Obtiene todos los scores."""
    scores = db.execute(select(Score).order_by(Score.id)).scalars().all()
    return [ScoreResponse(point=score.point) for score in scores]


@router.post("/", response_model=ScoreResponse)
def create_score(
        score_data: ScoreResponse,
        db: DbSession,
        current_user: Annotated[UserResponse, Depends(get_current_active_user)],
) -> ScoreResponse:
    """Crea un nuevo score (requiere autenticación)."""
    new_score = Score(point=score_data.point)
    db.add(new_score)
    db.commit()
    db.refresh(new_score)
    return ScoreResponse(point=new_score.point)
