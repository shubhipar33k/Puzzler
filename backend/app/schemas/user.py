from pydantic import BaseModel, ConfigDict
from typing import Optional
import datetime


class UserRegister(BaseModel):
    username: str
    email: str   # use pydantic[email] for full EmailStr validation in production
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: str
    username: str
    email: str
    current_skill_score: float
    streak_days: int
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class TokenData(BaseModel):
    user_id: Optional[str] = None
