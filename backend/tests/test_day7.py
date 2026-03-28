"""Tests for Day 7 — Logic grid engine and API integration."""
import pytest

from app.engines.logic import (
    generate_logic_puzzle,
    score_difficulty,
    band_from_score,
    PUZZLE_BANK,
)


# ── Engine unit tests ─────────────────────────────────────────────────────────

def test_generate_returns_required_keys():
    """generate_logic_puzzle() must return all expected keys."""
    result = generate_logic_puzzle("easy")
    required = {
        "categories", "items", "clues", "grid_size",
        "clue_count", "solution", "difficulty_score", "difficulty_band",
    }
    assert required.issubset(result.keys()), f"Missing keys: {required - result.keys()}"


def test_categories_are_two():
    """Each puzzle must have exactly 2 categories."""
    for band in PUZZLE_BANK:
        result = generate_logic_puzzle(band)
        assert len(result["categories"]) == 2, f"Expected 2 categories in band {band}"


def test_items_match_grid_size():
    """Each category must have exactly grid_size items."""
    for band in PUZZLE_BANK:
        result = generate_logic_puzzle(band)
        for cat in result["categories"]:
            assert len(result["items"][cat]) == result["grid_size"], \
                f"Items count mismatch in {band}: {cat}"


def test_solution_complete():
    """Solution must map every item in category[0] to exactly one item in category[1]."""
    for band in PUZZLE_BANK:
        result = generate_logic_puzzle(band)
        cat0, cat1 = result["categories"]
        items0 = set(result["items"][cat0])
        items1 = set(result["items"][cat1])
        sol = result["solution"]
        assert set(sol.keys()) == items0, \
            f"Solution keys don't match category[0] items in {band}"
        assert set(sol.values()) == items1, \
            f"Solution values don't match category[1] items in {band}"


def test_solution_is_bijection():
    """Solution must be a bijection — no two keys map to the same value."""
    for band in PUZZLE_BANK:
        result = generate_logic_puzzle(band)
        values = list(result["solution"].values())
        assert len(values) == len(set(values)), \
            f"Solution has duplicate values in band {band}"


def test_clues_have_required_fields():
    """Every clue must have 'text', 'type', 'a', 'b'."""
    result = generate_logic_puzzle("medium")
    for clue in result["clues"]:
        assert "text" in clue, "Clue missing 'text'"
        assert "type" in clue, "Clue missing 'type'"
        assert "a" in clue,    "Clue missing 'a'"
        assert "b" in clue,    "Clue missing 'b'"


def test_clue_references_valid_items():
    """Clue 'a' must be in category[0] items and 'b' in category[1] items."""
    for band in PUZZLE_BANK:
        result = generate_logic_puzzle(band)
        cat0, cat1 = result["categories"]
        items0 = set(result["items"][cat0])
        items1 = set(result["items"][cat1])
        for clue in result["clues"]:
            assert clue["a"] in items0, \
                f"Clue 'a'={clue['a']} not in {cat0} items (band={band})"
            assert clue["b"] in items1, \
                f"Clue 'b'={clue['b']} not in {cat1} items (band={band})"


def test_score_difficulty_range():
    """score_difficulty() must return a value in [0, 1]."""
    for band in PUZZLE_BANK:
        result = generate_logic_puzzle(band)
        score = score_difficulty(result["grid_size"], result["clue_count"])
        assert 0.0 <= score <= 1.0, f"Score {score} out of [0, 1] for band {band}"


def test_harder_band_higher_score():
    """Expert should have a higher avg difficulty score than beginner."""
    beginner_scores = [
        score_difficulty(
            generate_logic_puzzle("beginner")["grid_size"],
            generate_logic_puzzle("beginner")["clue_count"],
        )
        for _ in range(5)
    ]
    expert_scores = [
        score_difficulty(
            generate_logic_puzzle("expert")["grid_size"],
            generate_logic_puzzle("expert")["clue_count"],
        )
        for _ in range(5)
    ]
    assert sum(expert_scores) / 5 >= sum(beginner_scores) / 5, \
        "Expert should have higher difficulty score than beginner"


def test_band_from_score_covers_all():
    """band_from_score must map across the full [0, 1] range."""
    assert band_from_score(0.05) == "beginner"
    assert band_from_score(0.28) == "easy"
    assert band_from_score(0.46) == "medium"
    assert band_from_score(0.65) == "hard"
    assert band_from_score(0.85) == "expert"


def test_unknown_band_falls_back():
    """Unknown band name must not crash — falls back to 'medium'."""
    result = generate_logic_puzzle("nonexistent_band")
    assert result["difficulty_band"] == "medium"


# ── API integration tests ─────────────────────────────────────────────────────

def test_generate_logic_api_structure(client):
    """POST /api/puzzle/generate with type=logic returns a validated puzzle."""
    resp = client.post("/api/puzzle/generate", json={
        "type": "logic", "difficulty_band": "easy",
    })
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["type"] == "logic"
    assert data["is_validated"] is True
    assert "categories" in data["data"]
    assert "clues" in data["data"]
    assert "grid_size" in data["data"]


def test_generate_logic_api_solution(client):
    """Logic puzzle API response must include a non-empty solution."""
    resp = client.post("/api/puzzle/generate", json={
        "type": "logic", "difficulty_band": "medium",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "assignments" in data["solution"], "Solution must have 'assignments' key"
    assert len(data["solution"]["assignments"]) > 0


def test_generate_logic_clues_present(client):
    """Logic puzzle must have at least 2 clues."""
    resp = client.post("/api/puzzle/generate", json={
        "type": "logic", "difficulty_band": "hard",
    })
    assert resp.status_code == 201
    clues = resp.json()["data"]["clues"]
    assert len(clues) >= 2, "Puzzle should have at least 2 clues"


@pytest.mark.parametrize("band", ["beginner", "easy", "medium", "hard", "expert"])
def test_all_logic_bands_generatable(client, band):
    """Every difficulty band should produce a valid logic puzzle via the API."""
    resp = client.post("/api/puzzle/generate", json={"type": "logic", "difficulty_band": band})
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["difficulty_band"] == band
    assert data["is_validated"] is True
    assert len(data["data"]["clues"]) >= 2
