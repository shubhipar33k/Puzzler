"""Session router: start, log events, complete puzzle sessions."""
import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models.session import Session, PlayerMetric
from app.models.puzzle import Puzzle
from app.models.user import User
from app.schemas.session import (
    SessionStart,
    SessionStartOut,
    SessionEvent,
    SessionComplete,
    SessionOut,
)

router = APIRouter(prefix="/session", tags=["session"])


@router.post("/start", response_model=SessionStartOut, status_code=201)
def start_session(payload: SessionStart, user_id: str, db: DBSession = Depends(get_db)):
    """Begin a new puzzle session for a user."""
    puzzle = db.query(Puzzle).filter(Puzzle.id == payload.puzzle_id).first()
    if not puzzle:
        raise HTTPException(status_code=404, detail="Puzzle not found")

    session = Session(
        user_id=user_id,
        puzzle_id=payload.puzzle_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/event", status_code=204)
def log_event(session_id: str, payload: SessionEvent, db: DBSession = Depends(get_db)):
    """Log a fine-grained player event (error, hint, hesitation, correct)."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.is_complete:
        raise HTTPException(status_code=400, detail="Session already completed")

    # Update aggregate counters
    if payload.event_type == "error":
        session.error_count += 1
    elif payload.event_type == "hint":
        session.hints_used += 1

    metric = PlayerMetric(
        session_id=session_id,
        event_type=payload.event_type,
        cell_id=payload.cell_id,
        value=payload.value,
        extra=payload.extra or {},
    )
    db.add(metric)
    db.commit()


@router.post("/{session_id}/complete", response_model=SessionOut)
def complete_session(
    session_id: str, payload: SessionComplete, db: DBSession = Depends(get_db)
):
    """Mark session complete and update player skill score + streak."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.is_complete and session.completed_at is not None:
        raise HTTPException(status_code=400, detail="Session already completed")

    session.is_complete = payload.is_correct
    session.time_seconds = payload.time_seconds
    session.completed_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(session)

    # ── Skill rating update ───────────────────────────────────────────────
    user = db.query(User).filter(User.id == session.user_id).first()
    puzzle = db.query(Puzzle).filter(Puzzle.id == session.puzzle_id).first()

    if user and puzzle:
        try:
            from app.services.skill_rating import update_skill, update_streak
            score_before, score_after = update_skill(user, session, puzzle, db)
            session.skill_score_before = score_before
            session.skill_score_after = score_after
            db.commit()
            db.refresh(session)

            # Update play streak
            update_streak(user, db)
        except Exception as exc:
            # Skill update failure should not break the session completion
            import logging
            logging.getLogger(__name__).error("Skill update failed: %s", exc)

    return session
