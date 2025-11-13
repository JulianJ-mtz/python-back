import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import and_, desc, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..models.scores import Score, TestMode, VALID_MODE_VALUES
from ..utils.custom_exceptions import (
    DatabaseOperationException,
    InvalidInputScoreException,
    InvalidScoreMetricsException,
    TooManyRequestsException,
)

load_dotenv()

logger = logging.getLogger(__name__)


def _get_positive_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        parsed = int(raw_value)
        if parsed < 0:
            raise ValueError
        return parsed
    except ValueError:
        logger.warning(
            "Invalid environment value for %s=%r. Falling back to %s.",
            name,
            raw_value,
            default,
        )
        return default


_SCORE_RATE_LIMIT_COUNT = _get_positive_int_env(
    "SCORE_SUBMISSION_MAX_REQUESTS",
    default=60,
)
_SCORE_RATE_LIMIT_WINDOW = _get_positive_int_env(
    "SCORE_SUBMISSION_WINDOW_SECONDS",
    default=60,
)


def _enforce_submission_rate_limit(db: Session, user_id: uuid.UUID) -> None:
    if _SCORE_RATE_LIMIT_COUNT == 0 or _SCORE_RATE_LIMIT_WINDOW == 0:
        return

    window_start = datetime.now(timezone.utc) - timedelta(
        seconds=_SCORE_RATE_LIMIT_WINDOW
    )
    stmt = select(func.count(Score.id)).where(
        Score.user_id == user_id, Score.created_at >= window_start
    )
    submission_count = db.execute(stmt).scalar_one()

    if submission_count >= _SCORE_RATE_LIMIT_COUNT:
        logger.info("Score submission limit reached", extra={"user_id": str(user_id)})
        raise TooManyRequestsException(
            detail="Score submission rate limit exceeded",
            retry_after=_SCORE_RATE_LIMIT_WINDOW,
        )


def create_score(
    db: Session,
    user_id: uuid.UUID,
    mode: TestMode,
    mode_value: int,
    total_clicks: int,
    correct_clicks: int,
    duration: float,
    consistency: Optional[float] = None,
) -> Score:
    """
    Creates a new score for any game mode.

    Args:
        user_id: User's UUID
        mode: Test mode (TestMode.TIME or TestMode.CLICKS)
        mode_value: Mode value (15, 30, 60 for time / 25, 50, 100 for clicks)
        total_clicks: Total clicks performed (including incorrect ones)
        correct_clicks: Number of correct clicks
        duration: Actual test duration in seconds
        consistency: Performance consistency (optional, 0-100)

    Returns:
        Score: The created score
    """
    if mode_value not in VALID_MODE_VALUES[mode]:
        raise InvalidInputScoreException(mode, mode_value, VALID_MODE_VALUES[mode])

    if total_clicks < 0 or correct_clicks < 0:
        raise InvalidScoreMetricsException(detail="Clicks must be non-negative")

    if correct_clicks > total_clicks:
        raise InvalidScoreMetricsException(
            detail="Correct clicks cannot exceed total clicks",
        )

    if duration <= 0:
        raise InvalidScoreMetricsException(detail="Duration must be greater than zero")

    if consistency is not None and not 0 <= consistency <= 100:
        raise InvalidScoreMetricsException(
            detail="Consistency must be between 0 and 100",
        )

    cps = correct_clicks / duration
    accuracy = (correct_clicks / total_clicks * 100) if total_clicks > 0 else 0.0

    _enforce_submission_rate_limit(db, user_id)

    new_score = Score(
        user_id=user_id,
        mode=mode.value,
        mode_value=mode_value,
        cps=cps,
        total_clicks=total_clicks,
        correct_clicks=correct_clicks,
        duration=duration,
        accuracy=accuracy,
        consistency=consistency,
    )
    db.add(new_score)

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception(
            "Failed to create score",
            extra={
                "user_id": str(user_id),
                "mode": mode.value,
                "mode_value": mode_value,
            },
        )
        raise DatabaseOperationException(detail="Unable to record score") from exc
    db.refresh(new_score)
    return new_score


def get_user_best_score(
    db: Session, user_id: uuid.UUID, mode: TestMode, mode_value: int
) -> Optional[Score]:
    """
    Gets the best score of a user for a specific mode and value.
    The best score is the one with the highest CPS.

    Args:
        user_id: User's UUID
        mode: Test mode
        mode_value: Mode value (e.g., 30 for time 30s, 50 for clicks 50)
    """
    stmt = (
        select(Score)
        .where(
            Score.user_id == user_id,
            Score.mode == mode.value,
            Score.mode_value == mode_value,
        )
        .order_by(desc(Score.cps))
        .limit(1)
    )

    return db.execute(stmt).scalars().first()


def get_user_scores(
    db: Session,
    user_id: uuid.UUID,
    mode: Optional[TestMode] = None,
    mode_value: Optional[int] = None,
    limit: int = 10,
) -> list[Score]:
    """
    Gets the latest scores of a user.

    Args:
        user_id: User's UUID
        mode: Filter by mode (optional)
        mode_value: Filter by mode value (optional)
        limit: Maximum number of results
    """
    if limit <= 0:
        raise InvalidScoreMetricsException(detail="Limit must be greater than zero")

    stmt = select(Score).where(Score.user_id == user_id)

    if mode:
        stmt = stmt.where(Score.mode == mode.value)

    if mode_value:
        stmt = stmt.where(Score.mode_value == mode_value)

    stmt = stmt.order_by(desc(Score.created_at)).limit(limit)

    results = db.execute(stmt).scalars().all()
    return list(results)


def get_user_average_stats(
    db: Session, user_id: uuid.UUID, mode: TestMode, mode_value: int, days: int = 30
) -> dict:
    """
    Calculates average statistics of a user for a specific mode.

    Returns:
        dict with: avg_cps, avg_accuracy, avg_consistency, total_tests
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = select(
        func.avg(Score.cps),
        func.avg(Score.accuracy),
        func.avg(Score.consistency),
        func.count(Score.id),
    ).where(
        Score.user_id == user_id,
        Score.mode == mode.value,
        Score.mode_value == mode_value,
        Score.created_at >= since,
    )

    avg_cps, avg_accuracy, avg_consistency, total_tests = db.execute(stmt).one()

    if total_tests == 0:
        return {
            "avg_cps": 0.0,
            "avg_accuracy": 0.0,
            "avg_consistency": 0.0,
            "total_tests": 0,
        }

    return {
        "avg_cps": float(avg_cps or 0.0),
        "avg_accuracy": float(avg_accuracy or 0.0),
        "avg_consistency": float(avg_consistency or 0.0),
        "total_tests": int(total_tests),
    }


def get_leaderboard(
    db: Session, mode: TestMode, mode_value: int, limit: int = 10
) -> list[Score]:
    """
    Gets the global leaderboard for a specific mode and value.
    Returns the best score of each user (highest CPS).

    Args:
        mode: Test mode (time or clicks)
        mode_value: Mode value (e.g., 30 for time 30s)
        limit: Number of results
    """
    # Subquery to get the best CPS of each user
    subquery = (
        select(Score.user_id, func.max(Score.cps).label("max_cps"))
        .where(Score.mode == mode.value, Score.mode_value == mode_value)
        .group_by(Score.user_id)
        .subquery()
    )

    stmt = (
        select(Score)
        .join(
            subquery,
            and_(
                Score.user_id == subquery.c.user_id,
                Score.cps == subquery.c.max_cps,
            ),
        )
        .where(Score.mode == mode.value, Score.mode_value == mode_value)
        .order_by(desc(Score.cps))
        .limit(limit)
    )

    results = db.execute(stmt).scalars().all()
    return list(results)


def get_user_personal_bests(db: Session, user_id: uuid.UUID) -> dict:
    """
    Gets the user's best scores for all modes and values.

    Returns:
        dict with structure:
        {
            "time": {"15": Score, "30": Score, "60": Score},
            "clicks": {"25": Score, "50": Score, "100": Score}
        }
    """
    stmt = select(Score).where(Score.user_id == user_id)
    all_scores = db.execute(stmt).scalars().all()

    result = {"time": {}, "clicks": {}}

    for score in all_scores:
        mode_key = score.mode
        value_key = str(score.mode_value)

        if mode_key not in result:
            result[mode_key] = {}

        # Save only if it doesn't exist or if the CPS is better
        if (
            value_key not in result[mode_key]
            or score.cps > result[mode_key][value_key].cps
        ):
            result[mode_key][value_key] = score

    return result
