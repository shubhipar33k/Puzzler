"""
Puzzler — Word Puzzle Engine
============================
Implements a masked-word (Hangman-style) puzzle generator.

The player is shown a word with some letters hidden as underscores and must
guess the missing letters one at a time.

Public API:
    generate_word_puzzle(band)  → dict ready for DB storage
    score_difficulty(word, mask_count) → float in [0, 1]
    band_from_score(score)      → band string
"""

from __future__ import annotations

import random
from typing import Optional

# ── Word Bank ─────────────────────────────────────────────────────────────────
# ~20 words per band, ordered by length and frequency in English.
# Beginner: 3-4 letter, very common
# Easy:     5-6 letter, common
# Medium:   6-7 letter, moderately common
# Hard:     7-9 letter, less common
# Expert:   9+ letter, obscure or technical

WORD_BANK: dict[str, list[str]] = {
    "beginner": [
        "cat", "dog", "sun", "map", "cup", "box", "key", "hat", "pen", "sky",
        "arm", "leg", "bag", "car", "bus", "top", "red", "big", "hot", "wet",
    ],
    "easy": [
        "plant", "tiger", "chair", "brave", "field", "globe", "happy", "knife",
        "light", "money", "night", "ocean", "piano", "queen", "river", "storm",
        "table", "uncle", "voice", "water",
    ],
    "medium": [
        "bridge", "castle", "desert", "engine", "famine", "glimpse", "humble",
        "insect", "jigsaw", "knight", "locket", "mirror", "noodle", "oyster",
        "pencil", "quiver", "rattle", "saddle", "telescope", "umbrella",
    ],
    "hard": [
        "alchemy", "balance", "blossom", "chimney", "delight", "eclipse",
        "falconer", "galloped", "hazelnut", "icicle", "javelin", "kaleidoscope",
        "labyrinth", "mahogany", "navigate", "obstacle", "paradise", "quarrel",
        "reckless", "sapphire",
    ],
    "expert": [
        "archipelago", "belligerent", "cacophony", "diphthong", "ephemeral",
        "flabbergast", "garrulous", "hieroglyphic", "idiosyncratic", "juxtapose",
        "kaleidoscopic", "labyrinthine", "magnanimous", "nonchalance", "obsequious",
        "palindrome", "quintessential", "recalcitrant", "supercilious", "ubiquitous",
    ],
}

# Hints per word (optional; fallback to generic hint based on length)
WORD_HINTS: dict[str, str] = {
    # beginner
    "cat": "A furry pet that meows", "dog": "Man's best friend",
    "sun": "The star at the centre of our solar system", "map": "Used for navigation",
    "cup": "You drink from it", "box": "A container with flat sides",
    "key": "Opens a lock", "hat": "Worn on your head",
    "pen": "Used for writing", "sky": "Above the clouds",
    # easy
    "plant": "A living organism that photosynthesises", "tiger": "Striped big cat",
    "chair": "You sit on it", "brave": "Having courage",
    "field": "Open land", "globe": "A spherical model of Earth",
    "happy": "Feeling joy", "knife": "A cutting tool",
    "light": "Electromagnetic radiation visible to the eye", "money": "Used as currency",
    "night": "The dark hours", "ocean": "A vast body of salt water",
    "piano": "A keyboard instrument", "queen": "Female monarch",
    "river": "A large natural stream of water", "storm": "Severe weather",
    "table": "A flat surface supported by legs", "uncle": "Parent's brother",
    "voice": "Sound produced by vocal cords", "water": "H₂O",
    # medium
    "bridge": "Spans a gap or river", "castle": "A medieval fortification",
    "desert": "A hot, arid landscape", "engine": "Converts energy to motion",
    "famine": "An extreme scarcity of food", "glimpse": "A brief look",
    "humble": "Not proud or arrogant", "insect": "A six-legged arthropod",
    "jigsaw": "A puzzle of interlocking pieces", "knight": "A medieval warrior on horseback",
    "locket": "A small ornamental case worn on a necklace",
    "mirror": "Reflects your image", "noodle": "A type of pasta",
    "oyster": "A shellfish", "pencil": "Used for drawing or writing",
    "quiver": "Tremble slightly; or a case for arrows",
    "rattle": "Makes a rapid succession of sharp sounds",
    "saddle": "A seat for riding a horse",
    "telescope": "A device for observing distant objects",
    "umbrella": "Protection from rain",
    # hard
    "labyrinth": "A complex maze", "sapphire": "A blue gemstone",
    "eclipse": "Blocking of light", "paradise": "A place of perfect happiness",
}


# ── Core helpers ──────────────────────────────────────────────────────────────

def _mask_word(word: str, mask_ratio: float) -> tuple[str, list[int]]:
    """Return a masked version of the word and indices of hidden letters.

    The mask_ratio controls what fraction of *unique* letter positions to hide.
    The first and last letters are always revealed so the word isn't entirely opaque.
    """
    indices = list(range(len(word)))
    # Always reveal first and last letter
    revealable = indices[1:-1] if len(word) > 2 else indices
    random.shuffle(revealable)

    n_to_hide = max(1, round(len(revealable) * mask_ratio))
    hidden_indices = set(revealable[:n_to_hide])

    masked = "".join("_" if i in hidden_indices else ch for i, ch in enumerate(word))
    return masked, sorted(hidden_indices)


def _mask_ratio_for_band(band: str) -> float:
    """Return the fraction of letters to hide per difficulty band."""
    return {
        "beginner": 0.25,
        "easy":     0.40,
        "medium":   0.55,
        "hard":     0.70,
        "expert":   0.85,
    }.get(band, 0.55)


# ── Difficulty scoring ────────────────────────────────────────────────────────

def score_difficulty(word: str, mask_count: int) -> float:
    """Return a composite difficulty score in [0.0, 1.0].

    Formula:
        length_ratio  = (len(word) - 3) / 12   # normalised to [0, 1] for 3-15 char words
        mask_ratio    = mask_count / len(word)
        score = 0.5 * length_ratio + 0.5 * mask_ratio
    """
    length_ratio = min(max((len(word) - 3) / 12.0, 0.0), 1.0)
    mask_ratio = mask_count / max(len(word), 1)
    score = 0.5 * length_ratio + 0.5 * mask_ratio
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

def generate_word_puzzle(
    difficulty_band: str = "medium",
    theme: Optional[str] = None,
) -> dict:
    """Generate a word puzzle for the requested difficulty band.

    Returns:
        word           — the target word (the solution)
        masked         — the word with hidden letters replaced by "_"
        hidden_indices — sorted list of 0-based indices that are masked
        hint           — a short clue about the word
        letter_count   — total number of letters
        mask_count     — number of hidden letters
        difficulty_score — float in [0, 1]
        difficulty_band  — band string
    """
    if difficulty_band not in WORD_BANK:
        difficulty_band = "medium"

    word = random.choice(WORD_BANK[difficulty_band])
    mask_ratio = _mask_ratio_for_band(difficulty_band)
    masked, hidden_indices = _mask_word(word, mask_ratio)

    hint = WORD_HINTS.get(word) or f"A {len(word)}-letter word"

    diff_score = score_difficulty(word, len(hidden_indices))

    return {
        "word":            word,
        "masked":          masked,
        "hidden_indices":  hidden_indices,
        "hint":            hint,
        "letter_count":    len(word),
        "mask_count":      len(hidden_indices),
        "difficulty_score": diff_score,
        "difficulty_band": difficulty_band,
    }
