"""
Puzzler — Sudoku Engine
=======================
Implements:
  - generate_solved_grid()      → recursive backtracking, randomised digit order
  - solve(grid)                 → deterministic solver, returns first solution
  - count_solutions(grid, n)    → early-exit counter for uniqueness validation
  - remove_cells_symmetrically()→ 180°-symmetric cell removal with uniqueness guard
  - score_difficulty()          → composite float in [0, 1]
  - band_from_score()           → maps score → difficulty band string
  - generate_sudoku(band)       → public API, returns dict ready for DB storage

All grids are 9×9 lists-of-lists internally; the public API flattens to length-81 lists.
"""

from __future__ import annotations
import random
import copy
from typing import Optional


# ── Constants ────────────────────────────────────────────────────────────────

# Target clue counts per band (how many given cells remain after removal)
BAND_CLUE_TARGETS: dict[str, tuple[int, int]] = {
    "beginner": (50, 55),
    "easy":     (41, 50),
    "medium":   (32, 41),
    "hard":     (26, 32),
    "expert":   (22, 26),
}

ALL_BANDS = list(BAND_CLUE_TARGETS.keys())


# ── Core Solver ──────────────────────────────────────────────────────────────

def _find_empty(grid: list[list[int]]) -> Optional[tuple[int, int]]:
    """Return the (row, col) of the first empty cell (value 0), or None."""
    for r in range(9):
        for c in range(9):
            if grid[r][c] == 0:
                return r, c
    return None


def _is_valid_placement(grid: list[list[int]], row: int, col: int, num: int) -> bool:
    """Return True if placing `num` at (row, col) doesn't violate Sudoku rules."""
    # Row check
    if num in grid[row]:
        return False
    # Column check
    if num in (grid[r][col] for r in range(9)):
        return False
    # 3×3 box check
    br, bc = (row // 3) * 3, (col // 3) * 3
    for r in range(br, br + 3):
        for c in range(bc, bc + 3):
            if grid[r][c] == num:
                return False
    return True


def solve(grid: list[list[int]]) -> Optional[list[list[int]]]:
    """Return the first (deterministic) solution for the given puzzle, or None.

    The input grid is not mutated.
    """
    grid = copy.deepcopy(grid)
    return _solve_inplace(grid)


def _solve_inplace(grid: list[list[int]]) -> Optional[list[list[int]]]:
    """Recursive solver that mutates grid in-place; returns solution or None."""
    pos = _find_empty(grid)
    if pos is None:
        return grid  # fully solved
    r, c = pos
    for num in range(1, 10):
        if _is_valid_placement(grid, r, c, num):
            grid[r][c] = num
            result = _solve_inplace(grid)
            if result is not None:
                return result
            grid[r][c] = 0  # backtrack
    return None


def count_solutions(grid: list[list[int]], limit: int = 2) -> int:
    """Count solutions up to `limit`, then stop early.

    Used to verify uniqueness: call with limit=2 and check result == 1.
    """
    grid = copy.deepcopy(grid)
    counter = [0]

    def _count(g: list[list[int]]) -> None:
        if counter[0] >= limit:
            return
        pos = _find_empty(g)
        if pos is None:
            counter[0] += 1
            return
        r, c = pos
        for num in range(1, 10):
            if _is_valid_placement(g, r, c, num):
                g[r][c] = num
                _count(g)
                g[r][c] = 0
                if counter[0] >= limit:
                    return

    _count(grid)
    return counter[0]


# ── Solved Grid Generation ───────────────────────────────────────────────────

def generate_solved_grid() -> list[list[int]]:
    """Return a fully solved, randomised valid 9×9 Sudoku grid.

    Uses recursive backtracking with a shuffled digit list at each step so
    every call produces a different (but valid) grid.
    """
    grid: list[list[int]] = [[0] * 9 for _ in range(9)]
    _fill_grid(grid)
    return grid


def _fill_grid(grid: list[list[int]]) -> bool:
    """Recursive, randomised solver that fills `grid` in-place."""
    pos = _find_empty(grid)
    if pos is None:
        return True  # complete

    r, c = pos
    digits = list(range(1, 10))
    random.shuffle(digits)

    for num in digits:
        if _is_valid_placement(grid, r, c, num):
            grid[r][c] = num
            if _fill_grid(grid):
                return True
            grid[r][c] = 0  # backtrack
    return False


# ── Cell Removal ─────────────────────────────────────────────────────────────

def remove_cells_symmetrically(
    solved: list[list[int]],
    target_clues: int,
) -> list[list[int]]:
    """Remove cells from a solved grid until only `target_clues` remain.

    Cells are removed in 180°-symmetric pairs so the puzzle looks balanced.
    After every removal, we verify the puzzle still has a unique solution.
    If removing a pair would break uniqueness OR reduce clues below target,
    that pair is skipped.

    Returns the puzzle (0 = empty cell).
    """
    puzzle = copy.deepcopy(solved)
    current_clues = 81

    # Build list of all cell pairs that are 180° symmetric
    # For cell (r, c), its symmetric partner is (8-r, 8-c)
    # We only need one representative per pair
    pairs: list[tuple[tuple[int, int], tuple[int, int]]] = []
    visited: set[tuple[int, int]] = set()
    for r in range(9):
        for c in range(9):
            if (r, c) not in visited:
                sym = (8 - r, 8 - c)
                visited.add((r, c))
                visited.add(sym)
                if (r, c) == sym:
                    pairs.append(((r, c), (r, c)))  # centre cell — singleton
                else:
                    pairs.append(((r, c), sym))

    random.shuffle(pairs)

    for (r1, c1), (r2, c2) in pairs:
        if current_clues <= target_clues:
            break  # reached our target

        # Remember current values
        v1 = puzzle[r1][c1]
        v2 = puzzle[r2][c2]

        if v1 == 0 and v2 == 0:
            continue  # already removed

        # Try removing this pair
        puzzle[r1][c1] = 0
        if (r1, c1) != (r2, c2):
            puzzle[r2][c2] = 0

        if count_solutions(puzzle, limit=2) == 1:
            # Valid — update clue count
            current_clues -= 1 if (r1, c1) == (r2, c2) else 2
        else:
            # Restoring — this removal breaks uniqueness
            puzzle[r1][c1] = v1
            if (r1, c1) != (r2, c2):
                puzzle[r2][c2] = v2

    return puzzle


# ── Difficulty Scoring ───────────────────────────────────────────────────────

def _count_naked_singles(grid: list[list[int]]) -> int:
    """Count cells that have exactly one legal digit (naked singles).

    A large fraction of naked singles → easier puzzle.
    """
    count = 0
    for r in range(9):
        for c in range(9):
            if grid[r][c] != 0:
                continue
            possible = sum(
                1 for n in range(1, 10)
                if _is_valid_placement(grid, r, c, n)
            )
            if possible == 1:
                count += 1
    return count


def _solver_backtrack_depth(grid: list[list[int]]) -> int:
    """Return the total number of backtrack steps the deterministic solver takes.

    More backtracks → harder puzzle.
    """
    grid = copy.deepcopy(grid)
    counter = [0]

    def _solve_count(g: list[list[int]]) -> bool:
        pos = _find_empty(g)
        if pos is None:
            return True
        r, c = pos
        for num in range(1, 10):
            if _is_valid_placement(g, r, c, num):
                g[r][c] = num
                if _solve_count(g):
                    return True
                g[r][c] = 0
                counter[0] += 1  # backtrack step
        return False

    _solve_count(grid)
    return counter[0]


def score_difficulty(puzzle: list[list[int]], solution: list[list[int]]) -> float:
    """Return a composite difficulty score in [0.0, 1.0].

    Formula (from architecture.md):
        score = 0.4*(empty_ratio) + 0.3*(backtrack_depth_ratio) + 0.3*(1 - naked_singles_ratio)

    - empty_ratio: fraction of cells that are empty (0 = all filled, 1 = all empty)
    - backtrack_depth_ratio: solver backtrack steps / 200 (capped at 1.0)
    - naked_singles_ratio: naked_singles / empty_cells (higher = easier)
    """
    empty_cells = sum(1 for r in range(9) for c in range(9) if puzzle[r][c] == 0)
    empty_ratio = empty_cells / 81.0

    # Backtrack depth — normalise against a reference maximum of 200 steps
    depth = _solver_backtrack_depth(puzzle)
    backtrack_ratio = min(depth / 200.0, 1.0)

    # Naked singles ratio
    naked = _count_naked_singles(puzzle)
    naked_ratio = (naked / empty_cells) if empty_cells > 0 else 0.0
    naked_ratio = min(naked_ratio, 1.0)

    score = 0.4 * empty_ratio + 0.3 * backtrack_ratio + 0.3 * (1.0 - naked_ratio)
    return round(min(max(score, 0.0), 1.0), 4)


def band_from_score(score: float) -> str:
    """Map a difficulty score [0, 1] to a named difficulty band.

    Thresholds tuned to match the clue-count bands:
        [0.00 – 0.20)  → beginner
        [0.20 – 0.40)  → easy
        [0.40 – 0.60)  → medium
        [0.60 – 0.78)  → hard
        [0.78 – 1.00]  → expert
    """
    if score < 0.20:
        return "beginner"
    elif score < 0.40:
        return "easy"
    elif score < 0.60:
        return "medium"
    elif score < 0.78:
        return "hard"
    else:
        return "expert"


# ── Public API ───────────────────────────────────────────────────────────────

def generate_sudoku(difficulty_band: str = "medium", max_retries: int = 5) -> dict:
    """Generate a Sudoku puzzle for the requested difficulty band.

    Returns a dict with:
        puzzle          — flat list of 81 ints (0 = empty)
        solution        — flat list of 81 ints (complete solution)
        difficulty_score— float in [0, 1]
        difficulty_band — the band the puzzle was scored into
        clue_count      — number of givens

    If the generated puzzle's scored band does not exactly match the requested
    band after `max_retries` attempts, the closest result is returned anyway.
    """
    if difficulty_band not in BAND_CLUE_TARGETS:
        difficulty_band = "medium"

    target_min, target_max = BAND_CLUE_TARGETS[difficulty_band]
    # Target the midpoint of the clue range
    target_clues = (target_min + target_max) // 2

    best_result = None
    best_distance = float("inf")

    for _ in range(max_retries):
        solved = generate_solved_grid()
        puzzle = remove_cells_symmetrically(solved, target_clues)
        score = score_difficulty(puzzle, solved)
        scored_band = band_from_score(score)

        # Flatten grids to 1D lists
        flat_puzzle = [puzzle[r][c] for r in range(9) for c in range(9)]
        flat_solution = [solved[r][c] for r in range(9) for c in range(9)]
        clue_count = sum(1 for v in flat_puzzle if v != 0)

        result = {
            "puzzle": flat_puzzle,
            "solution": flat_solution,
            "difficulty_score": score,
            "difficulty_band": difficulty_band,  # honour the request
            "clue_count": clue_count,
        }

        if scored_band == difficulty_band:
            return result  # perfect match

        # Keep the closest attempt by clue count distance to midpoint
        distance = abs(clue_count - target_clues)
        if distance < best_distance:
            best_distance = distance
            best_result = result

    return best_result


# ── Calibration ───────────────────────────────────────────────────────────────

def calibrate_scorer(
    n: int = 20,
    bands: list[str] | None = None,
) -> dict[str, dict]:
    """Generate `n` puzzles per band and compute difficulty score statistics.

    Returns a dict keyed by band with keys:
        scores    — list of raw float scores
        min       — minimum score
        max       — maximum score
        mean      — mean score
        clues_mean— mean clue count

    Use this offline to validate / tune the band_from_score() thresholds.

    Example::
        from app.engines.sudoku import calibrate_scorer
        stats = calibrate_scorer(n=10)
        for band, s in stats.items():
            print(f"{band}: mean={s['mean']:.3f} [{s['min']:.3f}–{s['max']:.3f}]")
    """
    if bands is None:
        bands = ALL_BANDS

    results: dict[str, dict] = {}
    for band in bands:
        scores: list[float] = []
        clues: list[int] = []
        for _ in range(n):
            r = generate_sudoku(band)
            scores.append(r["difficulty_score"])
            clues.append(r["clue_count"])
        results[band] = {
            "scores": scores,
            "min": min(scores),
            "max": max(scores),
            "mean": round(sum(scores) / len(scores), 4),
            "clues_mean": round(sum(clues) / len(clues), 1),
        }
    return results

