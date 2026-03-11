import uuid
import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, JSON
from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class Session(Base):
    """One puzzle attempt by a user."""
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    puzzle_id = Column(String, ForeignKey("puzzles.id"), nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    time_seconds = Column(Integer, nullable=True)
    error_count = Column(Integer, default=0)
    hints_used = Column(Integer, default=0)
    is_complete = Column(Boolean, default=False)
    skill_score_before = Column(Float, nullable=True)
    skill_score_after = Column(Float, nullable=True)

    def __repr__(self):
        return f"<Session user={self.user_id} puzzle={self.puzzle_id} complete={self.is_complete}>"


class PlayerMetric(Base):
    """Fine-grained per-event tracking within a session."""
    __tablename__ = "player_metrics"

    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)  # error | hint | hesitation | correct
    cell_id = Column(String, nullable=True)       # grid cell or word position
    value = Column(String, nullable=True)         # what the user entered
    extra = Column(JSON, default={})              # flexible extra data
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class SkillSnapshot(Base):
    """Time-series of player skill scores for modeling."""
    __tablename__ = "skill_snapshots"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    skill_score = Column(Float, nullable=False)
    confidence = Column(Float, default=1.0)       # model confidence in the estimate
    puzzle_type = Column(String, nullable=True)   # per-type skill tracking
    recorded_at = Column(DateTime, default=datetime.datetime.utcnow)
