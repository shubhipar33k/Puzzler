from pydantic import BaseModel, ConfigDict
from typing import Optional, Any, Dict
import datetime


class PuzzleOut(BaseModel):
    id: str
    type: str
    difficulty_score: float
    difficulty_band: str
    data: Dict[str, Any]
    solution: Dict[str, Any]   # included so frontend can drive correctness checks
    is_validated: bool
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class PuzzleGenerateRequest(BaseModel):
    type: str = "sudoku"  # sudoku | word | crossword | logic
    difficulty_band: str = "medium"  # beginner | easy | medium | hard | expert
    theme: Optional[str] = None  # for word/crossword puzzles


class PuzzleWithSolution(PuzzleOut):
    solution: Dict[str, Any]
