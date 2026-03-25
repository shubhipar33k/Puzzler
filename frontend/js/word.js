/* ─────────────────────────────────────────────────────
   Puzzler — Word Puzzle
   Renders a masked-word (Hangman-style) puzzle:
     · Letter tiles showing revealed / hidden positions
     · A–Z on-screen keyboard
     · Wrong-guess counter with visual feedback
   Fires custom DOM events:
     word:correct  — player revealed all letters
     word:wrong    — wrong guess (detail: { letter, wrongCount })
     word:letter   — any guess (correct or not)
─────────────────────────────────────────────────────── */

class WordBoard {
    /**
     * @param {string} containerId   — ID of the container element
     * @param {object} puzzleData    — from API: { masked, hint, letter_count, mask_count }
     * @param {object} solution      — from API: { word }
     * @param {object} meta          — { difficulty_band, puzzle_id }
     */
    constructor(containerId, puzzleData, solution, meta = {}) {
        this.container = document.getElementById(containerId);
        this.word = (solution?.word || '').toLowerCase();
        this.masked = puzzleData?.masked || '';
        this.hint = puzzleData?.hint || '';
        this.meta = meta;

        // State
        this.revealed = new Set();          // correctly guessed letters
        this.wrong = new Set();          // wrong guesses
        this.isComplete = false;
        this.maxWrong = 6;

        // Build the current display: revealed[i] = known from mask, else must be guessed
        this._initRevealed();
        this._render();
    }

    /** Pre-populate revealed set from the initial masked string. */
    _initRevealed() {
        for (let i = 0; i < this.masked.length; i++) {
            if (this.masked[i] !== '_') {
                this.revealed.add(this.word[i]);
            }
        }
    }

    /** Full render of the word tiles + keyboard + status. */
    _render() {
        if (!this.container) return;
        this.container.innerHTML = `
            <div class="word-meta">
                <span class="word-band-pill">${this.meta.difficulty_band || 'medium'}</span>
                <span class="word-hint">💡 ${this.hint}</span>
            </div>

            <div class="word-tiles" id="word-tiles"></div>

            <div class="word-status">
                <div class="wrong-counter">
                    <span class="wrong-label">Wrong guesses:</span>
                    <span class="wrong-hearts" id="wrong-hearts"></span>
                    <span class="wrong-count" id="wrong-count">${this.wrong.size} / ${this.maxWrong}</span>
                </div>
                <div class="word-result" id="word-result"></div>
            </div>

            <div class="word-keyboard" id="word-keyboard"></div>
        `;

        this._renderTiles();
        this._renderHearts();
        this._renderKeyboard();
    }

    _renderTiles() {
        const container = document.getElementById('word-tiles');
        if (!container) return;
        container.innerHTML = this.word.split('').map((ch, i) => {
            const revealed = this.revealed.has(ch);
            return `<div class="word-tile ${revealed ? 'revealed' : 'hidden'}" data-index="${i}">
                <span class="tile-letter">${revealed ? ch.toUpperCase() : ''}</span>
            </div>`;
        }).join('');
    }

    _renderHearts() {
        const el = document.getElementById('wrong-hearts');
        if (!el) return;
        const hearts = Array.from({ length: this.maxWrong }, (_, i) =>
            `<span class="heart ${i < this.wrong.size ? 'lost' : 'alive'}">♥</span>`
        ).join('');
        el.innerHTML = hearts;
        const countEl = document.getElementById('wrong-count');
        if (countEl) countEl.textContent = `${this.wrong.size} / ${this.maxWrong}`;
    }

    _renderKeyboard() {
        const kb = document.getElementById('word-keyboard');
        if (!kb) return;
        const rows = [
            'QWERTYUIOP'.split(''),
            'ASDFGHJKL'.split(''),
            'ZXCVBNM'.split(''),
        ];
        kb.innerHTML = rows.map(row => `
            <div class="kb-row">
                ${row.map(ch => {
            const lower = ch.toLowerCase();
            const state = this.revealed.has(lower) ? 'correct'
                : this.wrong.has(lower) ? 'wrong'
                    : '';
            return `<button class="kb-key ${state}"
                                    data-letter="${lower}"
                                    id="kb-${lower}"
                                    ${state ? 'disabled' : ''}>${ch}</button>`;
        }).join('')}
            </div>
        `).join('');

        kb.querySelectorAll('.kb-key:not([disabled])').forEach(btn => {
            btn.addEventListener('click', () => this.guess(btn.dataset.letter));
        });
    }

    /** Handle a letter guess. */
    guess(letter) {
        letter = letter.toLowerCase();
        if (this.isComplete) return;
        if (this.revealed.has(letter) || this.wrong.has(letter)) return;

        const isCorrect = this.word.includes(letter);
        if (isCorrect) {
            this.revealed.add(letter);
            this._animateTiles(letter);
        } else {
            this.wrong.add(letter);
            this._shakeContainer();
        }

        this._renderTiles();
        this._renderHearts();
        this._updateKey(letter, isCorrect);

        // Dispatch events
        this.container.dispatchEvent(new CustomEvent('word:letter', {
            bubbles: true,
            detail: { letter, correct: isCorrect, wrongCount: this.wrong.size },
        }));

        if (!isCorrect) {
            this.container.dispatchEvent(new CustomEvent('word:wrong', {
                bubbles: true,
                detail: { letter, wrongCount: this.wrong.size },
            }));
        }

        // Check win / lose
        const allRevealed = this.word.split('').every(ch => this.revealed.has(ch));
        if (allRevealed) {
            this.isComplete = true;
            this._showResult('win');
            this.container.dispatchEvent(new CustomEvent('word:correct', { bubbles: true }));
        } else if (this.wrong.size >= this.maxWrong) {
            this.isComplete = true;
            this._showResult('lose');
            this.container.dispatchEvent(new CustomEvent('word:failed', {
                bubbles: true,
                detail: { word: this.word },
            }));
        }
    }

    _updateKey(letter, correct) {
        const btn = document.getElementById(`kb-${letter}`);
        if (!btn) return;
        btn.classList.add(correct ? 'correct' : 'wrong');
        btn.disabled = true;
    }

    _animateTiles(letter) {
        if (!this.container) return;
        this.word.split('').forEach((ch, i) => {
            if (ch === letter) {
                const tile = this.container.querySelector(`[data-index="${i}"]`);
                if (tile) {
                    tile.classList.add('pop');
                    setTimeout(() => tile.classList.remove('pop'), 400);
                }
            }
        });
    }

    _shakeContainer() {
        const tiles = document.getElementById('word-tiles');
        if (!tiles) return;
        tiles.classList.add('shake');
        setTimeout(() => tiles.classList.remove('shake'), 350);
    }

    _showResult(outcome) {
        const el = document.getElementById('word-result');
        if (!el) return;
        if (outcome === 'win') {
            el.innerHTML = `<span class="word-win">🎉 Solved! The word was <strong>${this.word.toUpperCase()}</strong></span>`;
        } else {
            el.innerHTML = `<span class="word-lose">💀 The word was <strong>${this.word.toUpperCase()}</strong></span>`;
        }
        // Reveal all tiles
        this.word.split('').forEach(ch => this.revealed.add(ch));
        this._renderTiles();
    }

    /** Reset to initial state (same puzzle). */
    reset() {
        this.revealed.clear();
        this.wrong.clear();
        this.isComplete = false;
        this._initRevealed();
        this._render();
    }
}
