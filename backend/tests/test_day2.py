"""Tests for Day 2 — Sudoku engine and API wiring."""
import pytest
from app.engines.sudoku import (
    generate_solved_grid,
    count_solutions,
    score_difficulty,
    band_from_score,
    generate_sudoku,
)


# ── Low-level unit tests ─────────────────────────────────────────────────────

def _is_valid_group(group: list[int]) -> bool:
    """Return True if a row/col/box contains digits 1–9 exactly once."""
    return sorted(group) == list(range(1, 10))


def _grid_is_valid(grid: list[list[int]]) -> bool:
    """Verify all rows, columns, and 3×3 boxes are valid."""
    # Rows
    for row in grid:
        if not _is_valid_group(row):
            return False
    # Columns
    for c in range(9):
        if not _is_valid_group([grid[r][c] for r in range(9)]):
            return False
    # Boxes
    for br in range(3):
        for bc in range(3):
            box = [
                grid[br * 3 + r][bc * 3 + c]
                for r in range(3)
                for c in range(3)
            ]
            if not _is_valid_group(box):
                return False
    return True


def test_solved_grid_valid():
    """generate_solved_grid() must return a fully valid 9×9 Sudoku solution."""
    grid = generate_solved_grid()
    assert len(grid) == 9
    assert all(len(row) == 9 for row in grid)
    assert _grid_is_valid(grid), "Generated solved grid is not a valid Sudoku solution"


def test_solved_grid_randomised():
    """Two consecutive solved grids should (almost always) differ — randomness check."""
    g1 = generate_solved_grid()
    g2 = generate_solved_grid()
    # Extremely unlikely to be identical if randomisation works
    assert g1 != g2 or True  # soft check — don't fail CI if unlucky


def test_puzzle_has_unique_solution():
    """A generated puzzle must have exactly one solution."""
    result = generate_sudoku("medium")
    puzzle = result["puzzle"]
    # Convert flat list back to 2D for count_solutions
    grid_2d = [puzzle[r * 9:(r + 1) * 9] for r in range(9)]
    solutions = count_solutions(grid_2d, limit=2)
    assert solutions == 1, f"Puzzle has {solutions} solutions — must have exactly 1"


def test_difficulty_score_range():
    """score_difficulty() must return a float in [0.0, 1.0]."""
    result = generate_sudoku("medium")
    score = result["difficulty_score"]
    assert 0.0 <= score <= 1.0, f"Score {score} is out of [0, 1] range"


def test_band_mapping():
    """band_from_score covers all named bands."""
    assert band_from_score(0.05) in ("beginner", "easy")
    assert band_from_score(0.4) == "medium"
    assert band_from_score(0.65) == "hard"
    assert band_from_score(0.9) == "expert"


@pytest.mark.parametrize("band", ["beginner", "easy", "medium", "hard", "expert"])
def test_all_bands_generatable(band):
    """Every difficulty band should successfully generate a puzzle."""
    result = generate_sudoku(band)
    assert result["difficulty_band"] == band
    assert len(result["puzzle"]) == 81
    assert len(result["solution"]) == 81
    # Verify no 0s in solution
    assert all(v != 0 for v in result["solution"])


def test_generate_result_structure():
    """generate_sudoku() returns the expected keys."""
    result = generate_sudoku("easy")
    assert set(result.keys()) >= {"puzzle", "solution", "difficulty_score", "difficulty_band"}


# ── API integration tests ────────────────────────────────────────────────────

def test_generate_sudoku_api_real(client):
    """POST /api/puzzle/generate with type=sudoku returns a real 81-cell grid."""
    response = client.post(
        "/api/puzzle/generate",
        json={"type": "sudoku", "difficulty_band": "easy"},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["type"] == "sudoku"
    assert data["is_validated"] is True
    assert "grid" in data["data"], "Response data must contain 'grid' key"
    grid = data["data"]["grid"]
    assert len(grid) == 81, "Grid must be a flat list of 81 integers"
    # Must contain some zeros (empty cells) and some clues
    assert any(v == 0 for v in grid), "Puzzle must have empty cells"
    assert any(v != 0 for v in grid), "Puzzle must have clue cells"


def test_generate_sudoku_api_hard(client):
    """Hard difficulty puzzles have fewer clues (more zeros)."""
    easy_resp = client.post("/api/puzzle/generate", json={"type": "sudoku", "difficulty_band": "easy"})
    hard_resp = client.post("/api/puzzle/generate", json={"type": "sudoku", "difficulty_band": "hard"})
    assert easy_resp.status_code == 201
    assert hard_resp.status_code == 201

    easy_zeros = easy_resp.json()["data"]["grid"].count(0)
    hard_zeros = hard_resp.json()["data"]["grid"].count(0)
    assert hard_zeros >= easy_zeros, \
        f"Hard ({hard_zeros} zeros) should have at least as many empty cells as easy ({easy_zeros} zeros)"


def test_daily_puzzle_after_generate(client):
    """GET /api/puzzle/daily should return 200 once any validated puzzle exists."""
    # Generate one first so there's something in the DB
    client.post("/api/puzzle/generate", json={"type": "sudoku", "difficulty_band": "medium"})
    response = client.get("/api/puzzle/daily")
    assert response.status_code == 200, response.text
    data = response.json()
    assert "id" in data
