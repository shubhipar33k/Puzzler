"""Player router: profile, weaknesses, session history."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func

from app.database import get_db
from app.models.user import User
from app.models.session import Session, SkillSnapshot
from app.schemas.session import PlayerProfile, WeaknessReport

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

    # Count puzzle types
    type_counts: dict = {}
    for s in completed:
        pass  # TODO: join with Puzzle table on Day 9

    return PlayerProfile(
        id=user.id,
        username=user.username,
        current_skill_score=user.current_skill_score,
        streak_days=user.streak_days,
        sessions_completed=len(completed),
        average_time_seconds=avg_time,
        favorite_puzzle_type=None,  # filled in Day 9
    )


@router.get("/weaknesses", response_model=WeaknessReport)
def get_weaknesses(user_id: str, db: DBSession = Depends(get_db)):
    """Return the player weakness profile. Detailed analysis comes Day 10."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return WeaknessReport(
        user_id=user_id,
        weak_letters=[],        # populated Day 10
        weak_domains=[],        # populated Day 10
        avg_hesitation_seconds=0.0,
        recommended_focus="Keep playing to build your weakness profile!",
    )


@router.get("/history")
def get_history(user_id: str, db: DBSession = Depends(get_db)):
    """Return the last 20 completed sessions for a user."""
    sessions = (
        db.query(Session)
        .filter(Session.user_id == user_id)
        .order_by(Session.started_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": s.id,
            "puzzle_id": s.puzzle_id,
            "time_seconds": s.time_seconds,
            "error_count": s.error_count,
            "hints_used": s.hints_used,
            "is_complete": s.is_complete,
            "started_at": s.started_at,
        }
        for s in sessions
    ]
