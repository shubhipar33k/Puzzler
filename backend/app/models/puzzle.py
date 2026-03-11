import uuid
import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, JSON
from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class Puzzle(Base):
    __tablename__ = "puzzles"

    id = Column(String, primary_key=True, default=generate_uuid)
    type = Column(String, nullable=False, index=True)  # sudoku | word | crossword | logic
    difficulty_score = Column(Float, nullable=False, default=50.0)
    difficulty_band = Column(String, nullable=False, default="medium")  # beginner/easy/medium/hard/expert
    data = Column(JSON, nullable=False)       # puzzle-type-specific payload
    solution = Column(JSON, nullable=False)   # correct answer
    metadata_ = Column("metadata", JSON, default={})  # extra info (theme, word_length, etc.)
    is_validated = Column(Boolean, default=False)
    is_daily = Column(Boolean, default=False)
    daily_date = Column(String, nullable=True)  # YYYY-MM-DD for daily puzzles
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<Puzzle type={self.type} difficulty={self.difficulty_score:.1f}>"
