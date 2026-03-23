"""Player router: profile, skill history, weaknesses, session history."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func

from app.database import get_db
from app.models.user import User
from app.models.puzzle import Puzzle
from app.models.session import Session, SkillSnapshot, PlayerMetric
from app.schemas.session import PlayerProfile, WeaknessReport, SkillHistoryOut

router = APIRouter(prefix="/player", tags=["player"])


@router.get("/profile", response_model=PlayerProfile)
def get_profile(user_id: str, db: DBSession = Depends(get_db)):
    """Return the player's skill profile and stats."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    completed = (
        db.query(Session)
        .filter(Session.user_id == user_id, Session.is_complete == True)
        .all()
    )

    avg_time = None
    if completed:
        times = [s.time_seconds for s in completed if s.time_seconds]
        avg_time = sum(times) / len(times) if times else None

    # Determine favourite puzzle type by joining with puzzles
    fav_type = None
    if completed:
        puzzle_ids = [s.puzzle_id for s in completed]
        type_query = (
            db.query(Puzzle.type, func.count(Puzzle.type).label("cnt"))
            .filter(Puzzle.id.in_(puzzle_ids))
            .group_by(Puzzle.type)
            .order_by(func.count(Puzzle.type).desc())
            .first()
        )
        fav_type = type_query[0] if type_query else None

    return PlayerProfile(
        id=user.id,
        username=user.username,
        current_skill_score=user.current_skill_score,
        streak_days=user.streak_days,
        sessions_completed=len(completed),
        average_time_seconds=avg_time,
        favorite_puzzle_type=fav_type,
    )


@router.get("/skill-history", response_model=SkillHistoryOut)
def get_skill_history(user_id: str, limit: int = 50, db: DBSession = Depends(get_db)):
    """Return the last `limit` skill snapshots for the user, oldest first."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    snapshots = (
        db.query(SkillSnapshot)
        .filter(SkillSnapshot.user_id == user_id)
        .order_by(SkillSnapshot.recorded_at.asc())
        .limit(limit)
        .all()
    )

    return SkillHistoryOut(
        points=[
            {"skill_score": s.skill_score, "recorded_at": s.recorded_at}
            for s in snapshots
        ],
        current=user.current_skill_score,
    )


@router.get("/weaknesses", response_model=WeaknessReport)
def get_weaknesses(user_id: str, db: DBSession = Depends(get_db)):
    """Compute weakness profile from real PlayerMetric data."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get all sessions for this user
    user_session_ids = [
        s.id for s in db.query(Session.id).filter(Session.user_id == user_id).all()
    ]

    weak_cells: list[str] = []
    avg_hesitation = 0.0
    recommended = "Keep playing to build your weakness profile!"

    if user_session_ids:
        # Find most error-prone cell positions
        error_rows = (
            db.query(PlayerMetric.cell_id, func.count(PlayerMetric.cell_id).label("cnt"))
            .filter(
                PlayerMetric.session_id.in_(user_session_ids),
                PlayerMetric.event_type == "error",
                PlayerMetric.cell_id.isnot(None),
            )
            .group_by(PlayerMetric.cell_id)
            .order_by(func.count(PlayerMetric.cell_id).desc())
            .limit(5)
            .all()
        )
        weak_cells = [row.cell_id for row in error_rows]

        # Total errors and hints as a proxy for difficulty
        total_errors = (
            db.query(func.count(PlayerMetric.id))
            .filter(
                PlayerMetric.session_id.in_(user_session_ids),
                PlayerMetric.event_type == "error",
            )
            .scalar() or 0
        )
        total_hints = (
            db.query(func.count(PlayerMetric.id))
            .filter(
                PlayerMetric.session_id.in_(user_session_ids),
                PlayerMetric.event_type == "hint",
            )
            .scalar() or 0
        )

        if total_errors > 10:
            recommended = "Focus on cells in boxes you make the most errors."
        elif total_hints > 5:
            recommended = "Try solving without hints to build pattern recognition."
        elif len(user_session_ids) >= 3:
            recommended = "You're doing well! Try a harder difficulty band."

    return WeaknessReport(
        user_id=user_id,
        weak_letters=[],
        weak_domains=weak_cells,
        avg_hesitation_seconds=avg_hesitation,
        recommended_focus=recommended,
    )


@router.get("/history")
def get_history(user_id: str, limit: int = 20, db: DBSession = Depends(get_db)):
    """Return the last `limit` sessions for a user with puzzle metadata."""
    sessions = (
        db.query(Session)
        .filter(Session.user_id == user_id)
        .order_by(Session.started_at.desc())
        .limit(limit)
        .all()
    )

    # Enrich with puzzle data
    result = []
    for s in sessions:
        puzzle = db.query(Puzzle).filter(Puzzle.id == s.puzzle_id).first()
        result.append({
            "id": s.id,
            "puzzle_id": s.puzzle_id,
            "puzzle_type": puzzle.type if puzzle else "unknown",
            "difficulty_band": puzzle.difficulty_band if puzzle else None,
            "time_seconds": s.time_seconds,
            "error_count": s.error_count,
            "hints_used": s.hints_used,
            "is_complete": s.is_complete,
            "skill_score_before": s.skill_score_before,
            "skill_score_after": s.skill_score_after,
            "started_at": s.started_at.isoformat() if s.started_at else None,
        })
    return result
