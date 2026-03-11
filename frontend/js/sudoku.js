/* ─────────────────────────────────────────────────────
   Puzzler — Sudoku Engine (Frontend)
   Renders a playable 9×9 Sudoku grid with full
   cell selection, numpad input, error highlighting,
   and timer-integrated event logging.
───────────────────────────────────────────────────── */

/* ── Offline fallback puzzle (shown if API is unreachable) ── */
const DEMO_PUZZLE = [
    [5, 3, 0, 0, 7, 0, 0, 0, 0],
    [6, 0, 0, 1, 9, 5, 0, 0, 0],
    [0, 9, 8, 0, 0, 0, 0, 6, 0],

    [8, 0, 0, 0, 6, 0, 0, 0, 3],
    [4, 0, 0, 8, 0, 3, 0, 0, 1],
    [7, 0, 0, 0, 2, 0, 0, 0, 6],

    [0, 6, 0, 0, 0, 0, 2, 8, 0],
    [0, 0, 0, 4, 1, 9, 0, 0, 5],
    [0, 0, 0, 0, 8, 0, 0, 7, 9],
];

const DEMO_SOLUTION = [
    [5, 3, 4, 6, 7, 8, 9, 1, 2],
    [6, 7, 2, 1, 9, 5, 3, 4, 8],
    [1, 9, 8, 3, 4, 2, 5, 6, 7],

    [8, 5, 9, 7, 6, 1, 4, 2, 3],
    [4, 2, 6, 8, 5, 3, 7, 9, 1],
    [7, 1, 3, 9, 2, 4, 8, 5, 6],

    [9, 6, 1, 5, 3, 7, 2, 8, 4],
    [2, 8, 7, 4, 1, 9, 6, 3, 5],
    [3, 4, 5, 2, 8, 6, 1, 7, 9],
];

/**
 * Convert a flat 81-element grid from the API into a 9×9 2D array.
 * @param {number[]} flat - flat list of 81 ints (0 = empty)
 * @returns {number[][]}
 */
function flatTo2D(flat) {
    return Array.from({ length: 9 }, (_, r) => flat.slice(r * 9, r * 9 + 9));
}

/** SudokuBoard: manages state + DOM for one puzzle instance.
 *
 *  puzzle   — 9×9 array (0 = empty cell)   [default: offline DEMO]
 *  solution — 9×9 array (fully solved)      [default: offline DEMO]
 *  meta     — optional metadata from API (difficulty_band, clue_count, etc.)
 */
class SudokuBoard {
    constructor(containerId, puzzle = DEMO_PUZZLE, solution = DEMO_SOLUTION, meta = {}) {
        this.container = document.getElementById(containerId);
        this.puzzle = puzzle.map(row => [...row]);
        this.grid = puzzle.map(row => [...row]);  // live player grid
        this.solution = solution;
        this.meta = meta;
        this.selectedRow = null;
        this.selectedCol = null;
        this.isComplete = false;
        this.errorCells = new Set();

        this.render();
        this.bindNumpad();
        this.bindKeyboard();
    }

    /** Display the difficulty badge if metadata is present. */
    renderMeta() {
        const badge = document.getElementById('difficulty-badge');
        if (badge && this.meta.difficulty_band) {
            const label = this.meta.difficulty_band.charAt(0).toUpperCase()
                + this.meta.difficulty_band.slice(1);
            badge.textContent = label;
            badge.className = `difficulty-badge band-${this.meta.difficulty_band}`;
        }
        const clueEl = document.getElementById('clue-count');
        if (clueEl && this.meta.clue_count != null) {
            clueEl.textContent = `${this.meta.clue_count} clues`;
        }
    }

    /** Build the 81-cell DOM grid. */
    render() {
        this.container.innerHTML = '';
        for (let r = 0; r < 9; r++) {
            for (let c = 0; c < 9; c++) {
                const cell = document.createElement('div');
                cell.classList.add('sudoku-cell');
                cell.dataset.row = r;
                cell.dataset.col = c;

                // Box border classes
                if (c === 2 || c === 5) cell.classList.add('box-right');
                if (r === 2 || r === 5) cell.classList.add('row-end-3');

                const val = this.puzzle[r][c];
                if (val !== 0) {
                    cell.classList.add('given');
                    cell.textContent = val;
                } else {
                    cell.classList.add('editable');
                    const playerVal = this.grid[r][c];
                    if (playerVal !== 0) cell.textContent = playerVal;
                }

                cell.addEventListener('click', () => this.selectCell(r, c));
                this.container.appendChild(cell);
            }
        }
    }

    /** Select a cell and highlight related cells. */
    selectCell(row, col) {
        this.selectedRow = row;
        this.selectedCol = col;
        this.updateHighlights();
    }

    /** Refresh CSS state for all cells. */
    updateHighlights() {
        const cells = this.container.querySelectorAll('.sudoku-cell');
        cells.forEach(cell => {
            const r = +cell.dataset.row;
            const c = +cell.dataset.col;
            cell.classList.remove('selected', 'highlighted', 'error', 'correct');

            if (r === this.selectedRow && c === this.selectedCol) {
                cell.classList.add('selected');
            } else if (
                r === this.selectedRow ||
                c === this.selectedCol ||
                (Math.floor(r / 3) === Math.floor(this.selectedRow / 3) &&
                    Math.floor(c / 3) === Math.floor(this.selectedCol / 3))
            ) {
                cell.classList.add('highlighted');
            }
        });
    }

    /** Place a number in the selected editable cell. */
    enterValue(value) {
        const { selectedRow: r, selectedCol: c } = this;
        if (r === null || this.puzzle[r][c] !== 0) return;   // guard: given cell
        if (this.isComplete) return;

        this.grid[r][c] = value;
        const cell = this.getCellEl(r, c);

        if (value === 0) {
            cell.textContent = '';
            cell.classList.remove('error', 'correct');
            return;
        }

        cell.textContent = value;

        // Instant correctness check
        if (this.solution[r][c] === value) {
            cell.classList.add('correct');
            cell.classList.remove('error');
            this.checkCompletion();
        } else {
            cell.classList.add('error');
            cell.classList.remove('correct');
            // Dispatch error event for session tracker
            document.dispatchEvent(new CustomEvent('sudoku:error', { detail: { row: r, col: c, value } }));
        }
    }

    /** Return the DOM element for a given row/col. */
    getCellEl(r, c) {
        return this.container.querySelector(`[data-row="${r}"][data-col="${c}"]`);
    }

    /** Check if the entire board is correctly solved. */
    checkCompletion() {
        for (let r = 0; r < 9; r++) {
            for (let c = 0; c < 9; c++) {
                if (this.grid[r][c] !== this.solution[r][c]) return;
            }
        }
        this.isComplete = true;
        document.dispatchEvent(new CustomEvent('sudoku:complete'));
    }

    /** Wire the numpad buttons. */
    bindNumpad() {
        document.querySelectorAll('.num-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.enterValue(parseInt(btn.dataset.value, 10));
            });
        });
    }

    /** Allow keyboard 1–9 and Backspace/Delete. */
    bindKeyboard() {
        document.addEventListener('keydown', (e) => {
            if (e.key >= '1' && e.key <= '9') {
                this.enterValue(parseInt(e.key, 10));
            } else if (e.key === 'Backspace' || e.key === 'Delete' || e.key === '0') {
                this.enterValue(0);
            } else if (e.key === 'ArrowUp' && this.selectedRow > 0) { this.selectCell(this.selectedRow - 1, this.selectedCol); }
            else if (e.key === 'ArrowDown' && this.selectedRow < 8) { this.selectCell(this.selectedRow + 1, this.selectedCol); }
            else if (e.key === 'ArrowLeft' && this.selectedCol > 0) { this.selectCell(this.selectedRow, this.selectedCol - 1); }
            else if (e.key === 'ArrowRight' && this.selectedCol < 8) { this.selectCell(this.selectedRow, this.selectedCol + 1); }
        });
    }

    /** Reveal the correct value for the selected cell (hint). */
    showHint() {
        const { selectedRow: r, selectedCol: c } = this;
        if (r === null || this.puzzle[r][c] !== 0) return;
        this.enterValue(this.solution[r][c]);
        document.dispatchEvent(new CustomEvent('sudoku:hint', { detail: { row: r, col: c } }));
    }

    /** Reset all editable cells. */
    reset() {
        for (let r = 0; r < 9; r++) {
            for (let c = 0; c < 9; c++) {
                if (this.puzzle[r][c] === 0) {
                    this.grid[r][c] = 0;
                }
            }
        }
        this.isComplete = false;
        this.render();
        this.bindNumpad();
    }
}

/** Render the tiny preview Sudoku in the hero section. */
function renderHeroSudoku() {
    const container = document.getElementById('hero-sudoku');
    if (!container) return;
    container.innerHTML = '';

    // Show first 3 rows as a preview snippet
    for (let r = 0; r < 9; r++) {
        for (let c = 0; c < 9; c++) {
            const cell = document.createElement('div');
            cell.classList.add('mini-cell');
            if (c === 2 || c === 5) cell.classList.add('box-right');
            if (r === 2 || r === 5) cell.classList.add('box-bottom');

            const val = DEMO_PUZZLE[r][c];
            if (val !== 0) {
                cell.classList.add('given');
                cell.textContent = val;
            } else {
                cell.classList.add('empty');
            }
            container.appendChild(cell);
        }
    }
}
