"""
Puzzler — Puzzle Pool Service
=============================
Manages a pre-generated pool of validated puzzles so the API always has
ready-made puzzles for every difficulty band without generating them on-demand.

Public interface:
    ensure_daily_puzzle(db)          → called at startup, safe to call many times
    seed_daily_pool(db, ...)         → generate puzzles for today if needed
    get_pool_status(db)              → per-band counts + today's daily IDs
"""

from __future__ import annotations

import datetime
import logging

from sqlalchemy.orm import Session

from app.models.puzzle import Puzzle

logger = logging.getLogger(__name__)

# How many validated puzzles we want in stock per band at all times
POOL_SIZE_PER_BAND = 3

ALL_BANDS = ["beginner", "easy", "medium", "hard", "expert"]


# ── Internal helpers ─────────────────────────────────────────────────────────

def _today() -> str:
    return datetime.date.today().isoformat()


def _count_for_band(db: Session, band: str) -> int:
    return (
        db.query(Puzzle)
        .filter(Puzzle.type == "sudoku", Puzzle.difficulty_band == band, Puzzle.is_validated == True)
        .count()
    )


def _has_daily_for_band(db: Session, band: str, today: str) -> bool:
    return (
        db.query(Puzzle)
        .filter(
            Puzzle.type == "sudoku",
            Puzzle.difficulty_band == band,
            Puzzle.is_daily == True,
            Puzzle.daily_date == today,
        )
        .first()
    ) is not None


def _generate_and_store(db: Session, band: str) -> Puzzle:
    """Generate one puzzle for the given band and persist it."""
    from app.engines.sudoku import generate_sudoku

    result = generate_sudoku(band)
    puzzle = Puzzle(
        type="sudoku",
        difficulty_score=result["difficulty_score"],
        difficulty_band=result["difficulty_band"],
        data={
            "grid": result["puzzle"],
            "clue_count": result["clue_count"],
            "difficulty_band": result["difficulty_band"],
        },
        solution={"grid": result["solution"]},
        is_validated=True,
    )
    db.add(puzzle)
    db.commit()
    db.refresh(puzzle)
    return puzzle


def _mark_as_daily(db: Session, puzzle: Puzzle, today: str) -> None:
    puzzle.is_daily = True
    puzzle.daily_date = today
    db.commit()


# ── Public API ───────────────────────────────────────────────────────────────

def seed_daily_pool(
    db: Session,
    bands: list[str] | None = None,
    count_per_band: int = POOL_SIZE_PER_BAND,
) -> dict[str, int]:
    """Ensure at least `count_per_band` validated puzzles exist for each band,
    and mark one puzzle per band as today's daily.

    Returns a dict mapping band → number of puzzles generated this call.
    """
    if bands is None:
        bands = ALL_BANDS

    today = _today()
    generated: dict[str, int] = {}

    for band in bands:
        existing = _count_for_band(db, band)
        needed = max(0, count_per_band - existing)
        generated[band] = 0

        for _ in range(needed):
            try:
                _generate_and_store(db, band)
                generated[band] += 1
                logger.info("Generated %s puzzle for pool.", band)
            except Exception as exc:  # pragma: no cover
                logger.error("Failed to generate %s puzzle: %s", band, exc)

        # Mark today's daily for this band if not already done
        if not _has_daily_for_band(db, band, today):
            # Pick the most recently created validated puzzle for this band
            candidate = (
                db.query(Puzzle)
                .filter(
                    Puzzle.type == "sudoku",
                    Puzzle.difficulty_band == band,
                    Puzzle.is_validated == True,
                    Puzzle.is_daily == False,
                )
                .order_by(Puzzle.created_at.desc())
                .first()
            )
            if candidate:
                _mark_as_daily(db, candidate, today)
                logger.info("Marked puzzle %s as daily (%s, %s).", candidate.id, band, today)
            else:
                # Edge case: all puzzles already marked daily — generate one more
                try:
                    fresh = _generate_and_store(db, band)
                    _mark_as_daily(db, fresh, today)
                    generated[band] += 1
                except Exception as exc:  # pragma: no cover
                    logger.error("Could not create daily for %s: %s", band, exc)

    return generated


def ensure_daily_puzzle(db: Session) -> None:
    """Idempotent startup hook — seeds the pool if today's daily is missing.

    Safe to call multiple times; does nothing if the pool is already full.
    """
    today = _today()
    missing_bands = [
        band for band in ALL_BANDS
        if not _has_daily_for_band(db, band, today)
    ]

    if not missing_bands:
        logger.info("Puzzle pool up-to-date for %s.", today)
        return

    logger.info("Seeding puzzle pool for bands: %s", missing_bands)
    seed_daily_pool(db, bands=missing_bands)


def get_pool_status(db: Session) -> dict:
    """Return per-band puzzle counts and today's daily puzzle IDs."""
    today = _today()
    status: dict = {"date": today, "bands": {}}

    for band in ALL_BANDS:
        total = _count_for_band(db, band)
        daily = (
            db.query(Puzzle)
            .filter(
                Puzzle.type == "sudoku",
                Puzzle.difficulty_band == band,
                Puzzle.is_daily == True,
                Puzzle.daily_date == today,
            )
            .first()
        )
        status["bands"][band] = {
            "total_validated": total,
            "daily_puzzle_id": daily.id if daily else None,
        }

    return status
