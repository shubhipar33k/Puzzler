"""Tests for Day 4 — skill rating engine and session completion API."""
import datetime
import pytest

from app.services.skill_rating import (
    update_skill,
    update_streak,
    _expected_outcome,
    _time_bonus,
    _penalty_factor,
)
from app.models.user import User
from app.models.session import Session, SkillSnapshot
from app.models.puzzle import Puzzle
from tests.conftest import TestingSessionLocal


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def test_user(db):
    """Create and persist a test user with a neutral skill score."""
    import uuid, bcrypt
    pw = bcrypt.hashpw(b"test", bcrypt.gensalt()).decode()
    user = User(
        id=str(uuid.uuid4()),
        username=f"tester_{uuid.uuid4().hex[:6]}",
        email=f"t_{uuid.uuid4().hex[:6]}@test.com",
        hashed_password=pw,
        current_skill_score=50.0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def test_puzzle(db):
    """Create and persist a medium-difficulty test puzzle."""
    import uuid
    puzzle = Puzzle(
        id=str(uuid.uuid4()),
        type="sudoku",
        difficulty_score=0.5,
        difficulty_band="medium",
        data={"grid": [0] * 81, "clue_count": 36, "difficulty_band": "medium"},
        solution={"grid": list(range(1, 82))},
        is_validated=True,
    )
    db.add(puzzle)
    db.commit()
    db.refresh(puzzle)
    return puzzle


@pytest.fixture()
def test_session(db, test_user, test_puzzle):
    """Create and persist an in-progress session."""
    import uuid
    sess = Session(
        id=str(uuid.uuid4()),
        user_id=test_user.id,
        puzzle_id=test_puzzle.id,
        error_count=0,
        hints_used=0,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess


# ── Unit Tests: rating helpers ────────────────────────────────────────────────

def test_expected_outcome_equal_ratings():
    """Equal player and puzzle ratings should give ~0.5 expected outcome."""
    assert abs(_expected_outcome(50.0, 50.0) - 0.5) < 0.001


def test_expected_outcome_player_favoured():
    """Higher player rating → expected outcome > 0.5."""
    assert _expected_outcome(70.0, 50.0) > 0.5


def test_time_bonus_fast_solve():
    """Solving much faster than expected gives bonus > 1.0."""
    assert _time_bonus(60, "medium") > 1.0     # expected 480s, solved in 60


def test_time_bonus_slow_solve():
    """Solving much slower than expected gives penalty < 1.0."""
    assert _time_bonus(1440, "medium") < 1.0   # expected 480s, solved in 24min


def test_penalty_factor_clean_solve():
    """Zero errors, zero hints → no penalty (1.0)."""
    assert _penalty_factor(0, 0) == 1.0


def test_penalty_factor_many_errors():
    """Many errors should floor the penalty factor at 0.3."""
    assert _penalty_factor(20, 5) == pytest.approx(0.3)


# ── Integration Tests: update_skill ──────────────────────────────────────────

def test_skill_update_correct_solve(db, test_user, test_session, test_puzzle):
    """Correct solve at expected speed should increase skill score."""
    test_session.is_complete = True
    test_session.time_seconds = 480       # right on expected for medium
    test_session.error_count = 0
    test_session.hints_used = 0
    db.commit()

    before, after = update_skill(test_user, test_session, test_puzzle, db)
    assert before == pytest.approx(50.0)
    assert after > before, f"Expected skill increase, got {before}→{after}"


def test_skill_update_incorrect_solve(db, test_user, test_session, test_puzzle):
    """Incorrect solve should decrease skill score."""
    test_session.is_complete = False
    test_session.time_seconds = None
    db.commit()

    before, after = update_skill(test_user, test_session, test_puzzle, db)
    assert after < before, f"Expected skill decrease, got {before}→{after}"


def test_skill_update_creates_snapshot(db, test_user, test_session, test_puzzle):
    """update_skill must create a SkillSnapshot row."""
    test_session.is_complete = True
    test_session.time_seconds = 300
    db.commit()

    snapshots_before = db.query(SkillSnapshot).filter(
        SkillSnapshot.user_id == test_user.id
    ).count()
    update_skill(test_user, test_session, test_puzzle, db)
    snapshots_after = db.query(SkillSnapshot).filter(
        SkillSnapshot.user_id == test_user.id
    ).count()
    assert snapshots_after == snapshots_before + 1


def test_penalty_reduces_gain(db, test_user, test_session, test_puzzle):
    """Many errors should reduce the skill gain vs. a clean solve."""
    import copy, uuid

    # Clean solve session
    test_session.is_complete = True
    test_session.time_seconds = 480
    test_session.error_count = 0
    test_session.hints_used = 0
    db.commit()
    _, clean_after = update_skill(test_user, test_session, test_puzzle, db)
    clean_gain = clean_after - 50.0

    # Reset user skill
    test_user.current_skill_score = 50.0
    db.commit()

    # Messy solve
    messy_session = Session(
        id=str(uuid.uuid4()),
        user_id=test_user.id,
        puzzle_id=test_puzzle.id,
        is_complete=True,
        time_seconds=480,
        error_count=8,
        hints_used=2,
    )
    db.add(messy_session)
    db.commit()
    _, messy_after = update_skill(test_user, messy_session, test_puzzle, db)
    messy_gain = messy_after - 50.0

    assert messy_gain < clean_gain, \
        f"Messy gain ({messy_gain:.3f}) should be less than clean gain ({clean_gain:.3f})"


# ── Streak tests ──────────────────────────────────────────────────────────────

def test_streak_increments(db, test_user):
    """Playing on consecutive days increments streak."""
    yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    test_user.last_played_date = yesterday
    test_user.streak_days = 3
    db.commit()

    new_streak = update_streak(test_user, db)
    assert new_streak == 4


def test_streak_resets_after_gap(db, test_user):
    """A two-day gap resets streak to 1."""
    two_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=2)
    test_user.last_played_date = two_days_ago
    test_user.streak_days = 10
    db.commit()

    new_streak = update_streak(test_user, db)
    assert new_streak == 1


# ── API integration tests ─────────────────────────────────────────────────────

def test_start_session_api(client):
    """POST /api/session/start should create a session linked to a puzzle."""
    # First generate a puzzle we can reference
    gen_resp = client.post(
        "/api/puzzle/generate",
        json={"type": "sudoku", "difficulty_band": "easy"},
    )
    assert gen_resp.status_code == 201
    puzzle_id = gen_resp.json()["id"]

    resp = client.post(
        "/api/session/start",
        params={"user_id": "test-user-123"},
        json={"puzzle_id": puzzle_id},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["puzzle_id"] == puzzle_id
    assert "id" in data


def test_complete_session_api(client):
    """POST /session/{id}/complete should return updated skill_score_after."""
    # Generate puzzle
    gen_resp = client.post(
        "/api/puzzle/generate",
        json={"type": "sudoku", "difficulty_band": "medium"},
    )
    puzzle_id = gen_resp.json()["id"]

    # Register a user and get their id
    import uuid
    uname = f"skill_tester_{uuid.uuid4().hex[:6]}"
    reg = client.post("/api/auth/register", json={
        "username": uname,
        "email": f"{uname}@test.com",
        "password": "testpass",
    })
    assert reg.status_code == 201
    user_id = reg.json()["user"]["id"]

    # Start a session
    start = client.post(
        "/api/session/start",
        params={"user_id": user_id},
        json={"puzzle_id": puzzle_id},
    )
    assert start.status_code == 201
    session_id = start.json()["id"]

    # Complete it
    complete = client.post(
        f"/api/session/{session_id}/complete",
        json={"time_seconds": 300, "is_correct": True},
    )
    assert complete.status_code == 200
    data = complete.json()
    assert data["skill_score_after"] is not None
    assert data["skill_score_before"] is not None
    assert data["skill_score_after"] != data["skill_score_before"]
