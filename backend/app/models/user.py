import uuid
import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean
from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    current_skill_score = Column(Float, default=50.0)
    streak_days = Column(Integer, default=0)
    last_played_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<User {self.username} skill={self.current_skill_score:.1f}>"
