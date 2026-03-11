"""Puzzle router: daily puzzle, next adaptive puzzle, generate puzzle."""
import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models.puzzle import Puzzle
from app.schemas.puzzle import PuzzleOut, PuzzleGenerateRequest

router = APIRouter(prefix="/puzzle", tags=["puzzle"])


@router.get("/daily", response_model=PuzzleOut)
def get_daily_puzzle(db: DBSession = Depends(get_db)):
    """Return today's featured puzzle. Same for all users — NYT-style."""
    today = datetime.date.today().isoformat()
    puzzle = (
        db.query(Puzzle)
        .filter(Puzzle.is_daily == True, Puzzle.daily_date == today)
        .first()
    )
    if not puzzle:
        # Fallback: return the most recent validated puzzle
        puzzle = (
            db.query(Puzzle)
            .filter(Puzzle.is_validated == True)
            .order_by(Puzzle.created_at.desc())
            .first()
        )
    if not puzzle:
        raise HTTPException(status_code=404, detail="No daily puzzle available yet")
    return puzzle


@router.get("/next", response_model=PuzzleOut)
def get_next_puzzle(user_id: str, db: DBSession = Depends(get_db)):
    """Return the next puzzle selected by the Adaptive Difficulty Engine.

    Currently stubs to a random validated puzzle at medium difficulty.
    ADE integration happens on Day 8.
    """
    puzzle = (
        db.query(Puzzle)
        .filter(
            Puzzle.is_validated == True,
            Puzzle.difficulty_band == "medium",
        )
        .order_by(Puzzle.created_at.desc())
        .first()
    )
    if not puzzle:
        raise HTTPException(status_code=404, detail="No puzzles available")
    return puzzle


@router.post("/generate", response_model=PuzzleOut, status_code=201)
def generate_puzzle(payload: PuzzleGenerateRequest, db: DBSession = Depends(get_db)):
    """Generate and store a new puzzle.

    Currently returns a placeholder. Real engine integration happens Day 2–6.
    """
    placeholder_data = {
        "message": f"Puzzle generation for type='{payload.type}' is coming on Day 2-6!",
        "type": payload.type,
        "difficulty_band": payload.difficulty_band,
    }
    puzzle = Puzzle(
        type=payload.type,
        difficulty_score=50.0,
        difficulty_band=payload.difficulty_band,
        data=placeholder_data,
        solution={},
        is_validated=False,
    )
    db.add(puzzle)
    db.commit()
    db.refresh(puzzle)
    return puzzle


@router.get("/{puzzle_id}", response_model=PuzzleOut)
def get_puzzle(puzzle_id: str, db: DBSession = Depends(get_db)):
    """Fetch a specific puzzle by ID."""
    puzzle = db.query(Puzzle).filter(Puzzle.id == puzzle_id).first()
    if not puzzle:
        raise HTTPException(status_code=404, detail="Puzzle not found")
    return puzzle
