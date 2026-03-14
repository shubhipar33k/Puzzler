"""
Puzzler — Skill Rating Service
==============================
Implements an Elo-style Bayesian rating system to update player skill scores
after each puzzle session.

Public API:
    update_skill(user, session, puzzle, db) → (score_before, score_after)
    update_streak(user, db)                 → new streak count
"""

from __future__ import annotations

import datetime
import math
import logging

from sqlalchemy.orm import Session as DBSession

logger = logging.getLogger(__name__)

# ── Elo parameters ────────────────────────────────────────────────────────────

K_FACTOR = 16.0          # Standard Elo K-factor (controls update magnitude)
MIN_SCORE = 0.0
MAX_SCORE = 100.0

# Expected solve times (seconds) per difficulty band — used for time bonus
BAND_EXPECTED_TIMES: dict[str, int] = {
    "beginner": 180,
    "easy":     300,
    "medium":   480,
    "hard":     720,
    "expert":   1200,
}


# ── Core helpers ──────────────────────────────────────────────────────────────

def _expected_outcome(player_rating: float, puzzle_rating: float) -> float:
    """Logistic expected score for the player against a puzzle of given rating.

    Returns a float in (0, 1):  > 0.5 means player is favoured.
    """
    return 1.0 / (1.0 + math.pow(10.0, (puzzle_rating - player_rating) / 400.0))


def _time_bonus(time_seconds: int | None, difficulty_band: str) -> float:
    """Return a multiplier in [0.5, 1.5] based on solve speed vs. band average.

    - Faster than expected → bonus > 1.0 (up to 1.5×)
    - Slower than expected → penalty < 1.0 (down to 0.5×)
    - Unknown time → 1.0 (neutral)
    """
    if time_seconds is None or time_seconds <= 0:
        return 1.0
    expected = BAND_EXPECTED_TIMES.get(difficulty_band, 480)
    ratio = expected / time_seconds          # >1 means faster than expected
    return max(0.5, min(1.5, ratio))


def _penalty_factor(error_count: int, hints_used: int) -> float:
    """Return a reduction factor in [0.3, 1.0] for errors and hints.

    Each error costs 0.05 and each hint costs 0.1, floored at 0.3.
    """
    penalty = 1.0 - (error_count * 0.05) - (hints_used * 0.10)
    return max(0.3, min(1.0, penalty))


def _puzzle_elo(difficulty_score: float) -> float:
    """Convert a difficulty_score [0,1] → Elo rating on the same 0–100 scale
    shifted to be comparable to player ratings (centred around 50).
    """
    # Map 0→0, 0.5→50, 1.0→100 then shift into Elo-friendly range
    return difficulty_score * 100.0


# ── Public API ────────────────────────────────────────────────────────────────

def update_skill(user, session, puzzle, db: DBSession) -> tuple[float, float]:
    """Compute and apply Elo-style rating update after a completed session.

    Args:
        user    — SQLAlchemy User instance
        session — SQLAlchemy Session instance (must be complete)
        puzzle  — SQLAlchemy Puzzle instance
        db      — active database session

    Returns:
        (score_before, score_after) as floats in [0, 100]

    Side-effects:
        - Updates user.current_skill_score
        - Creates a SkillSnapshot row
        - Commits both changes
    """
    from app.models.session import SkillSnapshot

    score_before = float(user.current_skill_score)

    puzzle_rating = _puzzle_elo(puzzle.difficulty_score)
    expected = _expected_outcome(score_before, puzzle_rating)

    # Actual result: 1.0 for correct, 0.0 for incorrect
    actual_base = 1.0 if session.is_complete else 0.0

    # Apply modifiers (only meaningful on a correct solve)
    if session.is_complete:
        tb = _time_bonus(session.time_seconds, puzzle.difficulty_band)
        pf = _penalty_factor(session.error_count, session.hints_used)
        actual = actual_base * tb * pf
        actual = min(actual, 1.5)   # cap so extreme speed can't over-award
    else:
        actual = 0.0

    delta = K_FACTOR * (actual - expected)
    score_after = max(MIN_SCORE, min(MAX_SCORE, score_before + delta))
    score_after = round(score_after, 4)

    # Persist skill score update
    user.current_skill_score = score_after
    db.add(user)

    # Create time-series snapshot
    snapshot = SkillSnapshot(
        user_id=user.id,
        skill_score=score_after,
        confidence=1.0,
        puzzle_type=puzzle.type,
    )
    db.add(snapshot)
    db.commit()

    logger.info(
        "Skill update: user=%s puzzle_elo=%.1f expected=%.3f actual=%.3f "
        "delta=%.2f %s→%s",
        user.id, puzzle_rating, expected, actual, delta, score_before, score_after,
    )

    return score_before, score_after


def update_streak(user, db: DBSession) -> int:
    """Update the user's consecutive play streak.

    - If the user played yesterday → increment streak
    - If the user played today already → no change
    - Otherwise (gap or first play) → reset to 1

    Returns the new streak count.
    """
    today = datetime.date.today()
    last = user.last_played_date

    if last is not None:
        last_date = last.date() if isinstance(last, datetime.datetime) else last
        delta_days = (today - last_date).days
        if delta_days == 0:
            # Already played today — don't double-count
            return int(user.streak_days)
        elif delta_days == 1:
            user.streak_days = (user.streak_days or 0) + 1
        else:
            user.streak_days = 1   # gap breaks the streak
    else:
        user.streak_days = 1       # first ever play

    user.last_played_date = datetime.datetime.combine(today, datetime.time.min)
    db.add(user)
    db.commit()

    return int(user.streak_days)
