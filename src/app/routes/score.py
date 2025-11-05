from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.routing import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.database import get_db
from src.app.models import Score
from src.app.schemas import ScoreResponse
from .auth import get_current_user

DbSession = Annotated[Session, Depends(get_db)]
router = APIRouter(prefix="/score", tags=["score"])


@router.get("/", response_model=list[ScoreResponse])
def get_scores(db: DbSession):
    scores = db.execute(select(Score).order_by(Score.id)).scalars().all()
    return scores


@router.post("/", response_model=ScoreResponse)
def create_score(score: ScoreResponse, db: DbSession,
                 current_user: Annotated[str, Depends(get_current_user)]):
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    new_score = Score(point=score.point)

    db.add(new_score)
    db.commit()
    db.refresh(new_score)
    return new_score
