"""Tests for Day 6 — Word puzzle engine and API integration."""
import pytest
import uuid

from app.engines.word import (
    generate_word_puzzle,
    score_difficulty,
    band_from_score,
    WORD_BANK,
)


# ── Engine unit tests ─────────────────────────────────────────────────────────

def test_generate_returns_required_keys():
    """generate_word_puzzle() must return all expected keys."""
    result = generate_word_puzzle("easy")
    required = {"word", "masked", "hidden_indices", "hint",
                "letter_count", "mask_count", "difficulty_score", "difficulty_band"}
    assert required.issubset(result.keys()), f"Missing keys: {required - result.keys()}"


def test_word_from_correct_bank():
    """Generated word must come from the requested difficulty bank."""
    for band in WORD_BANK:
        result = generate_word_puzzle(band)
        assert result["word"] in WORD_BANK[band], \
            f"Word '{result['word']}' not in {band} bank"


def test_masked_length_matches_word():
    """Masked string must have the same length as the original word."""
    result = generate_word_puzzle("medium")
    assert len(result["masked"]) == len(result["word"])


def test_masked_has_underscores():
    """Masked string must contain at least one underscore."""
    result = generate_word_puzzle("medium")
    assert "_" in result["masked"], "Masked word should contain at least one underscore"


def test_mask_count_matches_indices():
    """mask_count must equal the number of hidden_indices."""
    result = generate_word_puzzle("hard")
    assert result["mask_count"] == len(result["hidden_indices"])


def test_revealed_positions_correct():
    """Non-hidden positions in masked string must match original word."""
    result = generate_word_puzzle("easy")
    word = result["word"]
    masked = result["masked"]
    hidden = set(result["hidden_indices"])
    for i, (w_ch, m_ch) in enumerate(zip(word, masked)):
        if i not in hidden:
            assert w_ch == m_ch, f"Revealed pos {i}: expected '{w_ch}', got '{m_ch}'"


def test_harder_band_more_hidden():
    """Expert band should hide a larger fraction of letters than beginner."""
    total_beginner_masked = sum(
        generate_word_puzzle("beginner")["mask_count"] /
        generate_word_puzzle("beginner")["letter_count"]
        for _ in range(5)
    ) / 5

    total_expert_masked = sum(
        generate_word_puzzle("expert")["mask_count"] /
        generate_word_puzzle("expert")["letter_count"]
        for _ in range(5)
    ) / 5

    assert total_expert_masked > total_beginner_masked, \
        "Expert should mask a higher proportion than beginner"


def test_score_difficulty_range():
    """score_difficulty() must return a value in [0, 1]."""
    for band in WORD_BANK:
        result = generate_word_puzzle(band)
        score = score_difficulty(result["word"], result["mask_count"])
        assert 0.0 <= score <= 1.0, f"Score {score} out of [0, 1] for band {band}"


def test_band_from_score_covers_all():
    """band_from_score must map across the full [0, 1] range."""
    assert band_from_score(0.05) == "beginner"
    assert band_from_score(0.28) == "easy"
    assert band_from_score(0.46) == "medium"
    assert band_from_score(0.65) == "hard"
    assert band_from_score(0.85) == "expert"


def test_unknown_band_falls_back():
    """Unknown band name must not crash — falls back to 'medium'."""
    result = generate_word_puzzle("nonexistent_band")
    assert result["difficulty_band"] == "medium"
    assert result["word"] in WORD_BANK["medium"]


# ── API integration tests ─────────────────────────────────────────────────────

def test_generate_word_api_structure(client):
    """POST /api/puzzle/generate with type=word returns a validated word puzzle."""
    resp = client.post("/api/puzzle/generate", json={
        "type": "word", "difficulty_band": "easy",
    })
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["type"] == "word"
    assert data["is_validated"] is True
    assert "masked" in data["data"]
    assert "hint" in data["data"]
    assert "letter_count" in data["data"]


def test_generate_word_api_solution_present(client):
    """Word puzzle API response must include the solution word."""
    resp = client.post("/api/puzzle/generate", json={
        "type": "word", "difficulty_band": "medium",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "word" in data["solution"], "Solution must contain the 'word' key"
    assert isinstance(data["solution"]["word"], str)
    assert len(data["solution"]["word"]) > 0


def test_generate_word_harder_band(client):
    """A hard word puzzle should have a higher difficulty_score than an easy one (on average)."""
    easy_scores = []
    hard_scores = []
    for _ in range(3):
        r = client.post("/api/puzzle/generate", json={"type": "word", "difficulty_band": "easy"})
        easy_scores.append(r.json()["difficulty_score"])
        r = client.post("/api/puzzle/generate", json={"type": "word", "difficulty_band": "hard"})
        hard_scores.append(r.json()["difficulty_score"])
    assert sum(hard_scores) / 3 > sum(easy_scores) / 3, \
        "Hard puzzles should have higher difficulty scores than easy ones"


@pytest.mark.parametrize("band", ["beginner", "easy", "medium", "hard", "expert"])
def test_all_word_bands_generatable(client, band):
    """Every difficulty band should produce a valid word puzzle via the API."""
    resp = client.post("/api/puzzle/generate", json={"type": "word", "difficulty_band": band})
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["difficulty_band"] == band
    assert data["is_validated"] is True
    assert "_" in data["data"]["masked"]
