"""Tests for Day 3 — puzzle pool service and daily rotation."""
import datetime
import pytest

from app.services.puzzle_pool import (
    seed_daily_pool,
    ensure_daily_puzzle,
    get_pool_status,
    ALL_BANDS,
)
from app.models.puzzle import Puzzle
from app.database import Base
from tests.conftest import TestingSessionLocal


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def db():
    """Yield a fresh in-memory DB session, rolling back after each test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# ── Pool seeding tests ────────────────────────────────────────────────────────

def test_pool_seed_creates_puzzles(db):
    """seed_daily_pool should create at least 1 puzzle per requested band."""
    bands = ["easy", "medium"]
    seed_daily_pool(db, bands=bands, count_per_band=1)
    for band in bands:
        count = (
            db.query(Puzzle)
            .filter(Puzzle.type == "sudoku", Puzzle.difficulty_band == band, Puzzle.is_validated == True)
            .count()
        )
        assert count >= 1, f"Expected ≥1 puzzle for band '{band}', got {count}"


def test_daily_puzzle_marked(db):
    """After seeding, exactly one puzzle per band should be marked is_daily for today."""
    today = datetime.date.today().isoformat()
    bands = ["easy", "medium"]
    seed_daily_pool(db, bands=bands, count_per_band=1)
    for band in bands:
        daily_count = (
            db.query(Puzzle)
            .filter(
                Puzzle.type == "sudoku",
                Puzzle.difficulty_band == band,
                Puzzle.is_daily == True,
                Puzzle.daily_date == today,
            )
            .count()
        )
        assert daily_count == 1, \
            f"Expected exactly 1 daily puzzle for band '{band}', got {daily_count}"


def test_ensure_daily_is_idempotent(db):
    """Running ensure_daily_puzzle twice must not create duplicate dailies."""
    today = datetime.date.today().isoformat()
    # Call twice
    ensure_daily_puzzle(db)
    ensure_daily_puzzle(db)
    for band in ALL_BANDS:
        daily_count = (
            db.query(Puzzle)
            .filter(
                Puzzle.type == "sudoku",
                Puzzle.difficulty_band == band,
                Puzzle.is_daily == True,
                Puzzle.daily_date == today,
            )
            .count()
        )
        assert daily_count <= 1, \
            f"Duplicate daily puzzles found for band '{band}' (count={daily_count})"


# ── Pool status tests ─────────────────────────────────────────────────────────

def test_get_pool_status_structure(db):
    """get_pool_status should return a dict with 'date' and per-band info."""
    seed_daily_pool(db, bands=["medium"], count_per_band=1)
    status = get_pool_status(db)
    assert "date" in status
    assert "bands" in status
    assert "medium" in status["bands"]
    band_info = status["bands"]["medium"]
    assert "total_validated" in band_info
    assert "daily_puzzle_id" in band_info
    assert band_info["total_validated"] >= 1


def test_pool_status_endpoint(client, db):
    """GET /api/puzzle/pool/status should return 200 with per-band counts."""
    # Seed so there's something to report
    seed_daily_pool(db, bands=["medium"], count_per_band=1)
    response = client.get("/api/puzzle/pool/status")
    assert response.status_code == 200
    data = response.json()
    assert "bands" in data
    assert "medium" in data["bands"]


# ── Daily endpoint test ───────────────────────────────────────────────────────

def test_daily_endpoint_returns_todays(client, db):
    """GET /api/puzzle/daily should return a puzzle marked is_daily for today."""
    today = datetime.date.today().isoformat()
    # Explicitly seed and mark a medium puzzle as today's daily
    seed_daily_pool(db, bands=["medium"], count_per_band=1)
    response = client.get("/api/puzzle/daily")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["type"] == "sudoku"


# ── Calibration tests ─────────────────────────────────────────────────────────

def test_calibrate_scorer_returns_stats():
    """calibrate_scorer should return per-band stats with correct keys."""
    from app.engines.sudoku import calibrate_scorer
    stats = calibrate_scorer(n=2, bands=["easy", "medium"])
    for band in ["easy", "medium"]:
        assert band in stats
        s = stats[band]
        assert "min" in s and "max" in s and "mean" in s and "clues_mean" in s
        assert 0.0 <= s["min"] <= s["max"] <= 1.0
        assert s["clues_mean"] > 0
