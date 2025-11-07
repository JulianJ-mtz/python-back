from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Query
from fastapi.routing import APIRouter
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_active_user
from ..models import User
from ..models.scores import TestMode
from ..schemas import (
    ScoreCreate,
    ScoreResponse,
    UserResponse,
    LeaderboardEntry,
    PersonalBests,
    AverageStats,
)
from ..services import score_service

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[UserResponse, Depends(get_current_active_user)]
router = APIRouter(prefix="/scores", tags=["scores"])


@router.post("/", response_model=ScoreResponse, status_code=201)
def create_score(
    score_data: ScoreCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> ScoreResponse:
    """
    Creates a new score for the authenticated user.

    - **mode**: "time" or "clicks"
    - **mode_value**: mode value (15, 30, 60 for time / 25, 50, 100 for clicks)
    - **total_clicks**: total clicks performed
    - **correct_clicks**: correct clicks
    - **duration**: duration in seconds
    - **consistency**: optional consistency (0-100)
    """
    # Validate mode
    if score_data.mode not in ["time", "clicks"]:
        raise HTTPException(
            status_code=400, detail="Invalid mode. Must be 'time' or 'clicks'"
        )

    mode = TestMode.TIME if score_data.mode == "time" else TestMode.CLICKS

    new_score = score_service.create_score(
        db=db,
        user_id=current_user.id,
        mode=mode,
        mode_value=score_data.mode_value,
        total_clicks=score_data.total_clicks,
        correct_clicks=score_data.correct_clicks,
        duration=score_data.duration,
        consistency=score_data.consistency,
    )

    return ScoreResponse(
        id=UUID(str(new_score.id)),
        user_id=UUID(str(new_score.user_id)),
        mode=new_score.mode,
        mode_value=new_score.mode_value,
        cps=new_score.cps,
        total_clicks=new_score.total_clicks,
        correct_clicks=new_score.correct_clicks,
        duration=new_score.duration,
        accuracy=new_score.accuracy,
        consistency=new_score.consistency,
        created_at=new_score.created_at.isoformat(),
    )


@router.get("/me", response_model=list[ScoreResponse])
def get_my_scores(
    db: DbSession,
    current_user: CurrentUser,
    mode: str | None = Query(None, description="Filter by mode: time or clicks"),
    mode_value: int | None = Query(None, description="Filter by mode value"),
    limit: int = Query(10, ge=1, le=100, description="Number of results"),
) -> list[ScoreResponse]:
    """
    Gets the authenticated user's scores, sorted by date (most recent first).

    Optional filters:
    - **mode**: "time" or "clicks"
    - **mode_value**: e.g., 30 for time 30s, 50 for clicks 50
    - **limit**: maximum number of results (1-100)
    """
    test_mode = None
    if mode:
        if mode not in ["time", "clicks"]:
            raise HTTPException(status_code=400, detail="Invalid mode")
        test_mode = TestMode.TIME if mode == "time" else TestMode.CLICKS

    scores = score_service.get_user_scores(
        db=db,
        user_id=current_user.id,
        mode=test_mode,
        mode_value=mode_value,
        limit=limit,
    )

    return [
        ScoreResponse(
            id=UUID(str(score.id)),
            user_id=UUID(str(score.user_id)),
            mode=score.mode,
            mode_value=score.mode_value,
            cps=score.cps,
            total_clicks=score.total_clicks,
            correct_clicks=score.correct_clicks,
            duration=score.duration,
            accuracy=score.accuracy,
            consistency=score.consistency,
            created_at=score.created_at.isoformat(),
        )
        for score in scores
    ]


@router.get("/me/best", response_model=ScoreResponse | None)
def get_my_best_score(
    db: DbSession,
    current_user: CurrentUser,
    mode: str = Query(..., description="Mode: time or clicks"),
    mode_value: int = Query(..., description="Mode value"),
) -> ScoreResponse | None:
    """
    Gets the user's best score for a specific mode and value.

    Example: GET /scores/me/best?mode=time&mode_value=30
    """
    if mode not in ["time", "clicks"]:
        raise HTTPException(status_code=400, detail="Invalid mode")

    test_mode = TestMode.TIME if mode == "time" else TestMode.CLICKS

    best_score = score_service.get_user_best_score(
        db=db,
        user_id=current_user.id,
        mode=test_mode,
        mode_value=mode_value,
    )

    if not best_score:
        return None

    return ScoreResponse(
        id=UUID(str(best_score.id)),
        user_id=UUID(str(best_score.user_id)),
        mode=best_score.mode,
        mode_value=best_score.mode_value,
        cps=best_score.cps,
        total_clicks=best_score.total_clicks,
        correct_clicks=best_score.correct_clicks,
        duration=best_score.duration,
        accuracy=best_score.accuracy,
        consistency=best_score.consistency,
        created_at=best_score.created_at.isoformat(),
    )


@router.get("/me/personal-bests", response_model=PersonalBests)
def get_my_personal_bests(
    db: DbSession,
    current_user: CurrentUser,
) -> PersonalBests:
    """
    Gets all user's personal records organized by mode.

    Returns:
    ```json
    {
        "time": {
            "15": {...},
            "30": {...},
            "60": {...}
        },
        "clicks": {
            "25": {...},
            "50": {...},
            "100": {...}
        }
    }
    ```
    """
    personal_bests = score_service.get_user_personal_bests(
        db=db, user_id=current_user.id
    )

    # Convert to ScoreResponse
    result = {"time": {}, "clicks": {}}

    for mode_key, mode_dict in personal_bests.items():
        for value_key, score in mode_dict.items():
            if score:
                result[mode_key][value_key] = ScoreResponse(
                    id=score.id,
                    user_id=score.user_id,
                    mode=score.mode,
                    mode_value=score.mode_value,
                    cps=score.cps,
                    total_clicks=score.total_clicks,
                    correct_clicks=score.correct_clicks,
                    duration=score.duration,
                    accuracy=score.accuracy,
                    consistency=score.consistency,
                    created_at=score.created_at.isoformat(),
                )
            else:
                result[mode_key][value_key] = None

    return PersonalBests(**result)


@router.get("/me/stats", response_model=AverageStats)
def get_my_average_stats(
    db: DbSession,
    current_user: CurrentUser,
    mode: str = Query(..., description="Mode: time or clicks"),
    mode_value: int = Query(..., description="Mode value"),
    days: int = Query(30, ge=1, le=365, description="Days to consider"),
) -> AverageStats:
    """
    Gets user's average statistics for a specific mode in the last X days.

    Returns: avg_cps, avg_accuracy, avg_consistency, total_tests
    """
    if mode not in ["time", "clicks"]:
        raise HTTPException(status_code=400, detail="Invalid mode")

    test_mode = TestMode.TIME if mode == "time" else TestMode.CLICKS

    stats = score_service.get_user_average_stats(
        db=db,
        user_id=current_user.id,
        mode=test_mode,
        mode_value=mode_value,
        days=days,
    )

    return AverageStats(**stats)


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
def get_leaderboard(
    db: DbSession,
    mode: str = Query(..., description="Mode: time or clicks"),
    mode_value: int = Query(..., description="Mode value"),
    limit: int = Query(10, ge=1, le=100, description="Number of results"),
) -> list[LeaderboardEntry]:
    """
    Gets the global leaderboard for a specific mode and value.
    Shows the best score of each user, sorted by CPS descending.

    Example: GET /scores/leaderboard?mode=time&mode_value=30&limit=10
    """
    if mode not in ["time", "clicks"]:
        raise HTTPException(status_code=400, detail="Invalid mode")

    test_mode = TestMode.TIME if mode == "time" else TestMode.CLICKS

    scores = score_service.get_leaderboard(
        db=db,
        mode=test_mode,
        mode_value=mode_value,
        limit=limit,
    )

    result = []
    for score in scores:
        # Get the user for each score
        user = db.query(User).filter(User.id == score.user_id).first()

        result.append(
            LeaderboardEntry(
                score=ScoreResponse(
                    id=UUID(str(score.id)),
                    user_id=UUID(str(score.user_id)),
                    mode=score.mode,
                    mode_value=score.mode_value,
                    cps=score.cps,
                    total_clicks=score.total_clicks,
                    correct_clicks=score.correct_clicks,
                    duration=score.duration,
                    accuracy=score.accuracy,
                    consistency=score.consistency,
                    created_at=score.created_at.isoformat(),
                ),
                user_email=user.email if user else "Unknown",
            )
        )

    return result
