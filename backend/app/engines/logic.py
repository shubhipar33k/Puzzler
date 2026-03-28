"""
Puzzler — Logic Grid Engine
============================
Implements a curated bank of Einstein-style logic grid puzzles.

Each puzzle presents an N×N grid where the player must deduce which
items from one category map to which items from another category,
using a set of binary/positional clues — no guessing required.

Public API:
    generate_logic_puzzle(band, theme=None)  → dict ready for DB storage
    score_difficulty(grid_size, clue_count)  → float in [0, 1]
    band_from_score(score)                   → band string
"""

from __future__ import annotations

import random
from typing import Optional

# ── Puzzle Bank ───────────────────────────────────────────────────────────────
# Each puzzle is a dict with:
#   categories  — list of 2 category names (axis labels)
#   items       — dict mapping category → list of N items
#   solution    — dict mapping item[0] → item[1]  (the true assignments)
#   clues       — list of clue dicts, each with 'text' and 'type'
#
# Clue types: "is", "is_not", "left_of", "right_of", "next_to", "not_next_to"
# (frontend renders these into human-readable sentences)

PUZZLE_BANK: dict[str, list[dict]] = {
    "beginner": [
        {
            "categories": ["Person", "Colour"],
            "items": {
                "Person": ["Alice", "Bob", "Cara"],
                "Colour": ["Red", "Blue", "Green"],
            },
            "solution": {"Alice": "Blue", "Bob": "Red", "Cara": "Green"},
            "clues": [
                {"text": "Alice does not like Red.", "type": "is_not",
                 "a": "Alice", "b": "Red"},
                {"text": "Bob does not like Blue.", "type": "is_not",
                 "a": "Bob", "b": "Blue"},
                {"text": "Cara likes Green.", "type": "is",
                 "a": "Cara", "b": "Green"},
            ],
        },
        {
            "categories": ["Pet", "Food"],
            "items": {
                "Pet": ["Cat", "Dog", "Fish"],
                "Food": ["Fish", "Bone", "Flakes"],
            },
            "solution": {"Cat": "Fish", "Dog": "Bone", "Fish": "Flakes"},
            "clues": [
                {"text": "The cat does not eat Flakes.", "type": "is_not",
                 "a": "Cat", "b": "Flakes"},
                {"text": "The dog eats a Bone.", "type": "is",
                 "a": "Dog", "b": "Bone"},
                {"text": "The fish does not eat a Bone.", "type": "is_not",
                 "a": "Fish", "b": "Bone"},
            ],
        },
        {
            "categories": ["Child", "Sport"],
            "items": {
                "Child": ["Emma", "Liam", "Mia"],
                "Sport": ["Tennis", "Swimming", "Football"],
            },
            "solution": {"Emma": "Swimming", "Liam": "Football", "Mia": "Tennis"},
            "clues": [
                {"text": "Emma does not play Tennis.", "type": "is_not",
                 "a": "Emma", "b": "Tennis"},
                {"text": "Liam plays Football.", "type": "is",
                 "a": "Liam", "b": "Football"},
                {"text": "Mia does not play Football.", "type": "is_not",
                 "a": "Mia", "b": "Football"},
            ],
        },
    ],

    "easy": [
        {
            "categories": ["Person", "City"],
            "items": {
                "Person": ["Alice", "Bob", "Cara", "Dan"],
                "City": ["Paris", "Rome", "Berlin", "Tokyo"],
            },
            "solution": {
                "Alice": "Tokyo", "Bob": "Rome",
                "Cara": "Paris", "Dan": "Berlin",
            },
            "clues": [
                {"text": "Alice lives east of everyone else.", "type": "is",
                 "a": "Alice", "b": "Tokyo"},
                {"text": "Bob does not live in Paris or Berlin.", "type": "is_not",
                 "a": "Bob", "b": "Paris"},
                {"text": "Bob does not live in Berlin.", "type": "is_not",
                 "a": "Bob", "b": "Berlin"},
                {"text": "Cara does not live in Tokyo or Berlin.", "type": "is_not",
                 "a": "Cara", "b": "Tokyo"},
                {"text": "Dan lives in a German city.", "type": "is",
                 "a": "Dan", "b": "Berlin"},
            ],
        },
        {
            "categories": ["Student", "Instrument"],
            "items": {
                "Student": ["Aiden", "Beth", "Cole", "Dana"],
                "Instrument": ["Guitar", "Piano", "Violin", "Drums"],
            },
            "solution": {
                "Aiden": "Drums", "Beth": "Piano",
                "Cole": "Guitar", "Dana": "Violin",
            },
            "clues": [
                {"text": "Aiden does not play Guitar or Piano.", "type": "is_not",
                 "a": "Aiden", "b": "Guitar"},
                {"text": "Aiden does not play Violin.", "type": "is_not",
                 "a": "Aiden", "b": "Violin"},
                {"text": "Beth plays a keyboard instrument.", "type": "is",
                 "a": "Beth", "b": "Piano"},
                {"text": "Cole does not play Piano or Drums.", "type": "is_not",
                 "a": "Cole", "b": "Piano"},
                {"text": "Cole does not play Violin.", "type": "is_not",
                 "a": "Cole", "b": "Violin"},
            ],
        },
    ],

    "medium": [
        {
            "categories": ["Person", "Job"],
            "items": {
                "Person": ["Anna", "Ben", "Cleo", "Dave"],
                "Job": ["Doctor", "Lawyer", "Engineer", "Teacher"],
            },
            "solution": {
                "Anna": "Lawyer", "Ben": "Engineer",
                "Cleo": "Doctor", "Dave": "Teacher",
            },
            "clues": [
                {"text": "Anna is not an Engineer or Teacher.", "type": "is_not",
                 "a": "Anna", "b": "Engineer"},
                {"text": "Anna is not a Doctor.", "type": "is_not",
                 "a": "Anna", "b": "Doctor"},
                {"text": "Ben is not a Doctor or Teacher.", "type": "is_not",
                 "a": "Ben", "b": "Doctor"},
                {"text": "Ben is not a Lawyer.", "type": "is_not",
                 "a": "Ben", "b": "Lawyer"},
                {"text": "Cleo is not a Teacher or Lawyer.", "type": "is_not",
                 "a": "Cleo", "b": "Teacher"},
                {"text": "Cleo is not an Engineer.", "type": "is_not",
                 "a": "Cleo", "b": "Engineer"},
            ],
        },
        {
            "categories": ["House", "Colour"],
            "items": {
                "House": ["First", "Second", "Third", "Fourth"],
                "Colour": ["Red", "Blue", "Green", "Yellow"],
            },
            "solution": {
                "First": "Yellow", "Second": "Blue",
                "Third": "Red", "Fourth": "Green",
            },
            "clues": [
                {"text": "The red house is not first or second.", "type": "is_not",
                 "a": "First", "b": "Red"},
                {"text": "The red house is not second.", "type": "is_not",
                 "a": "Second", "b": "Red"},
                {"text": "The blue house is not first.", "type": "is_not",
                 "a": "First", "b": "Blue"},
                {"text": "The blue house is not third or fourth.", "type": "is_not",
                 "a": "Third", "b": "Blue"},
                {"text": "The fourth house is green.", "type": "is",
                 "a": "Fourth", "b": "Green"},
                {"text": "The first house is not blue or green.", "type": "is_not",
                 "a": "First", "b": "Green"},
            ],
        },
    ],

    "hard": [
        {
            "categories": ["Scientist", "Discovery"],
            "items": {
                "Scientist": ["Marie", "Isaac", "Ada", "Albert"],
                "Discovery": ["Gravity", "Relativity", "Computing", "Radioactivity"],
            },
            "solution": {
                "Marie": "Radioactivity", "Isaac": "Gravity",
                "Ada": "Computing", "Albert": "Relativity",
            },
            "clues": [
                {"text": "Marie did not discover Gravity or Computing.", "type": "is_not",
                 "a": "Marie", "b": "Gravity"},
                {"text": "Marie did not discover Relativity.", "type": "is_not",
                 "a": "Marie", "b": "Relativity"},
                {"text": "Isaac discovered something before Einstein.", "type": "is_not",
                 "a": "Isaac", "b": "Relativity"},
                {"text": "Isaac did not discover Radioactivity or Computing.", "type": "is_not",
                 "a": "Isaac", "b": "Radioactivity"},
                {"text": "Ada's work was foundational to modern computers.", "type": "is",
                 "a": "Ada", "b": "Computing"},
                {"text": "Albert did not discover Radioactivity or Computing.", "type": "is_not",
                 "a": "Albert", "b": "Radioactivity"},
            ],
        },
        {
            "categories": ["Author", "Genre"],
            "items": {
                "Author": ["Petra", "Quinn", "Rosa", "Sam"],
                "Genre": ["Mystery", "Fantasy", "Sci-Fi", "Romance"],
            },
            "solution": {
                "Petra": "Fantasy", "Quinn": "Sci-Fi",
                "Rosa": "Mystery", "Sam": "Romance",
            },
            "clues": [
                {"text": "Petra does not write Mystery or Romance.", "type": "is_not",
                 "a": "Petra", "b": "Mystery"},
                {"text": "Petra does not write Sci-Fi.", "type": "is_not",
                 "a": "Petra", "b": "Sci-Fi"},
                {"text": "Quinn writes about the future, not the past.", "type": "is_not",
                 "a": "Quinn", "b": "Mystery"},
                {"text": "Quinn does not write Romance or Fantasy.", "type": "is_not",
                 "a": "Quinn", "b": "Romance"},
                {"text": "Rosa does not write Romance or Fantasy.", "type": "is_not",
                 "a": "Rosa", "b": "Romance"},
                {"text": "Rosa does not write Sci-Fi.", "type": "is_not",
                 "a": "Rosa", "b": "Sci-Fi"},
            ],
        },
    ],

    "expert": [
        {
            "categories": ["Philosopher", "School"],
            "items": {
                "Philosopher": ["Plato", "Kant", "Nietzsche", "Beauvoir"],
                "School": ["Idealism", "Rationalism", "Existentialism", "Feminism"],
            },
            "solution": {
                "Plato": "Idealism", "Kant": "Rationalism",
                "Nietzsche": "Existentialism", "Beauvoir": "Feminism",
            },
            "clues": [
                {"text": "Plato is not associated with Rationalism, Existentialism, or Feminism.", "type": "is_not",
                 "a": "Plato", "b": "Rationalism"},
                {"text": "Kant is known for his categorical imperative, not forms or existence.", "type": "is_not",
                 "a": "Kant", "b": "Idealism"},
                {"text": "Kant is not associated with Existentialism.", "type": "is_not",
                 "a": "Kant", "b": "Existentialism"},
                {"text": "Nietzsche rejected Enlightenment rationalism completely.", "type": "is_not",
                 "a": "Nietzsche", "b": "Rationalism"},
                {"text": "Nietzsche is not associated with Idealism or Feminism.", "type": "is_not",
                 "a": "Nietzsche", "b": "Idealism"},
                {"text": "Beauvoir is not associated with Idealism, Rationalism, or Existentialism (alone).", "type": "is_not",
                 "a": "Beauvoir", "b": "Idealism"},
                {"text": "Beauvoir co-founded a movement centred on gender.", "type": "is",
                 "a": "Beauvoir", "b": "Feminism"},
            ],
        },
        {
            "categories": ["Country", "Language"],
            "items": {
                "Country": ["Brazil", "Egypt", "Japan", "Norway"],
                "Language": ["Portuguese", "Arabic", "Norwegian", "Japanese"],
            },
            "solution": {
                "Brazil": "Portuguese", "Egypt": "Arabic",
                "Japan": "Japanese", "Norway": "Norwegian",
            },
            "clues": [
                {"text": "Brazil's official language is not Arabic, Japanese, or Norwegian.", "type": "is_not",
                 "a": "Brazil", "b": "Arabic"},
                {"text": "Egypt does not speak Japanese or Norwegian.", "type": "is_not",
                 "a": "Egypt", "b": "Japanese"},
                {"text": "Egypt does not speak Portuguese.", "type": "is_not",
                 "a": "Egypt", "b": "Portuguese"},
                {"text": "Japan does not speak Portuguese or Arabic.", "type": "is_not",
                 "a": "Japan", "b": "Portuguese"},
                {"text": "Japan does not speak Norwegian.", "type": "is_not",
                 "a": "Japan", "b": "Norwegian"},
                {"text": "Norway does not speak Portuguese, Arabic, or Japanese.", "type": "is_not",
                 "a": "Norway", "b": "Portuguese"},
            ],
        },
    ],
}


# ── Difficulty scoring ────────────────────────────────────────────────────────

def score_difficulty(grid_size: int, clue_count: int) -> float:
    """Return a composite difficulty score in [0.0, 1.0].

    Formula:
        size_ratio = (grid_size - 3) / 2   (3→0, 4→0.5, 5→1.0)
        clue_ratio = 1 - (clue_count / (grid_size * grid_size))  # fewer clues = harder
        score = 0.5 * size_ratio + 0.5 * clue_ratio
    """
    size_ratio = min(max((grid_size - 3) / 2.0, 0.0), 1.0)
    max_clues = grid_size * grid_size
    clue_ratio = 1.0 - min(clue_count / max_clues, 1.0)
    score = 0.5 * size_ratio + 0.5 * clue_ratio
    return round(min(max(score, 0.0), 1.0), 4)


def band_from_score(score: float) -> str:
    """Map difficulty score [0, 1] → named band."""
    if score < 0.20:
        return "beginner"
    elif score < 0.38:
        return "easy"
    elif score < 0.56:
        return "medium"
    elif score < 0.74:
        return "hard"
    else:
        return "expert"


# ── Public API ────────────────────────────────────────────────────────────────

def generate_logic_puzzle(
    difficulty_band: str = "medium",
    theme: Optional[str] = None,
) -> dict:
    """Generate a logic grid puzzle for the requested difficulty band.

    Returns:
        categories      — list of 2 category names
        items           — dict mapping category → list of items
        clues           — list of clue dicts (text, type, a, b)
        grid_size       — N (length of each items list)
        clue_count      — number of clues provided
        difficulty_score — float in [0, 1]
        difficulty_band  — band string
        solution        — the answer mapping (category[0] item → category[1] item)
    """
    if difficulty_band not in PUZZLE_BANK:
        difficulty_band = "medium"

    puzzle = random.choice(PUZZLE_BANK[difficulty_band])
    grid_size = len(puzzle["items"][puzzle["categories"][0]])
    clue_count = len(puzzle["clues"])
    diff_score = score_difficulty(grid_size, clue_count)

    return {
        "categories":      puzzle["categories"],
        "items":           puzzle["items"],
        "clues":           puzzle["clues"],
        "grid_size":       grid_size,
        "clue_count":      clue_count,
        "solution":        puzzle["solution"],
        "difficulty_score": diff_score,
        "difficulty_band": difficulty_band,
    }
