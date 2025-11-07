import uuid
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from src.app.models.scores import Score, TestMode, VALID_MODE_VALUES
from src.app.utils.custom_exceptions import InvalidInputScoreException


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
    # Calculate CPS based on correct clicks
    cps = correct_clicks / duration if duration > 0 else 0.0

    # Calculate accuracy
    accuracy = (correct_clicks / total_clicks * 100) if total_clicks > 0 else 0.0

    # Validate mode_value
    if mode_value not in VALID_MODE_VALUES[mode]:
        raise InvalidInputScoreException(mode, mode_value, VALID_MODE_VALUES[mode])

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
    db.commit()
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
    return (
        db.query(Score)
        .filter(
            Score.user_id == user_id,
            Score.mode == mode.value,
            Score.mode_value == mode_value,
        )
        .order_by(desc(Score.cps))
        .first()
    )


def get_user_scores(
    db: Session,
    user_id: uuid.UUID,
    mode: Optional[TestMode] = None,
    mode_value: Optional[int] = None,
    limit: int = 10,
) -> List[Score]:
    """
    Gets the latest scores of a user.

    Args:
        user_id: User's UUID
        mode: Filter by mode (optional)
        mode_value: Filter by mode value (optional)
        limit: Maximum number of results
    """
    query = db.query(Score).filter(Score.user_id == user_id)

    if mode:
        query = query.filter(Score.mode == mode.value)

    if mode_value:
        query = query.filter(Score.mode_value == mode_value)

    return query.order_by(desc(Score.created_at)).limit(limit).all()


def get_user_average_stats(
    db: Session, user_id: uuid.UUID, mode: TestMode, mode_value: int, days: int = 30
) -> dict:
    """
    Calculates average statistics of a user for a specific mode.

    Returns:
        dict with: avg_cps, avg_accuracy, avg_consistency, total_tests
    """
    since = datetime.utcnow() - timedelta(days=days)

    scores = (
        db.query(Score)
        .filter(
            Score.user_id == user_id,
            Score.mode == mode.value,
            Score.mode_value == mode_value,
            Score.created_at >= since,
        )
        .all()
    )

    if not scores:
        return {
            "avg_cps": 0.0,
            "avg_accuracy": 0.0,
            "avg_consistency": 0.0,
            "total_tests": 0,
        }

    total = len(scores)
    consistency_scores = [s.consistency for s in scores if s.consistency is not None]

    return {
        "avg_cps": sum(s.cps for s in scores) / total,
        "avg_accuracy": sum(s.accuracy for s in scores) / total,
        "avg_consistency": sum(consistency_scores) / len(consistency_scores)
        if consistency_scores
        else 0.0,
        "total_tests": total,
    }


def get_leaderboard(
    db: Session, mode: TestMode, mode_value: int, limit: int = 10
) -> List[Score]:
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
        db.query(Score.user_id, func.max(Score.cps).label("max_cps"))
        .filter(Score.mode == mode.value, Score.mode_value == mode_value)
        .group_by(Score.user_id)
        .subquery()
    )

    # Main query
    return (
        db.query(Score)
        .join(
            subquery,
            (Score.user_id == subquery.c.user_id) & (Score.cps == subquery.c.max_cps),
        )
        .filter(Score.mode == mode.value, Score.mode_value == mode_value)
        .order_by(desc(Score.cps))
        .limit(limit)
        .all()
    )


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
    all_scores = db.query(Score).filter(Score.user_id == user_id).all()

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
