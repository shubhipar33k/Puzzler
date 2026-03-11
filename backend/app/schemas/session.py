from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
import datetime


class SessionStart(BaseModel):
    puzzle_id: str


class SessionStartOut(BaseModel):
    id: str
    puzzle_id: str
    started_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class SessionEvent(BaseModel):
    event_type: str          # error | hint | hesitation | correct
    cell_id: Optional[str] = None
    value: Optional[str] = None
    extra: Optional[Dict[str, Any]] = {}


class SessionComplete(BaseModel):
    time_seconds: int
    is_correct: bool


class SessionOut(BaseModel):
    id: str
    puzzle_id: str
    started_at: datetime.datetime
    completed_at: Optional[datetime.datetime]
    time_seconds: Optional[int]
    error_count: int
    hints_used: int
    is_complete: bool
    skill_score_before: Optional[float]
    skill_score_after: Optional[float]

    model_config = ConfigDict(from_attributes=True)


class PlayerProfile(BaseModel):
    id: str
    username: str
    current_skill_score: float
    streak_days: int
    sessions_completed: int
    average_time_seconds: Optional[float]
    favorite_puzzle_type: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class WeaknessReport(BaseModel):
    user_id: str
    weak_letters: list[str]
    weak_domains: list[str]
    avg_hesitation_seconds: float
    recommended_focus: str
