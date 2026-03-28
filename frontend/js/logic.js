/* ─────────────────────────────────────────────────────
   Puzzler — Logic Grid Puzzle
   Renders an Einstein-style two-axis deduction grid:
     · N×N truth table (✓ / ✗ / blank per cell)
     · Clue panel listing all given constraints
     · Auto-validates when all cells are filled
   Fires custom DOM events:
     logic:correct  — all assignments correctly deduced
     logic:error    — incorrect cell detected
─────────────────────────────────────────────────────── */

class LogicBoard {
    /**
     * @param {string} containerId   — ID of the container element
     * @param {object} puzzleData    — { categories, items, clues, grid_size }
     * @param {object} solution      — { assignments: { itemA: itemB, ... } }
     * @param {object} meta          — { difficulty_band, puzzle_id }
     */
    constructor(containerId, puzzleData, solution, meta = {}) {
        this.container = document.getElementById(containerId);
        this.categories = puzzleData?.categories || [];
        this.items = puzzleData?.items || {};
        this.clues = puzzleData?.clues || [];
        this.gridSize = puzzleData?.grid_size || 3;
        this.solution = solution?.assignments || {};
        this.meta = meta;

        // player's current marks: { "row§col": "yes"|"no"|"" }
        this.marks = {};
        this.isComplete = false;

        this._render();
    }

    _render() {
        if (!this.container) return;
        const [catRow, catCol] = this.categories;
        const rows = this.items[catRow] || [];
        const cols = this.items[catCol] || [];

        this.container.innerHTML = `
            <div class="logic-meta">
                <span class="logic-band-pill">${this.meta.difficulty_band || 'medium'}</span>
                <span class="logic-cats">${catRow} <span class="logic-vs">↔</span> ${catCol}</span>
            </div>

            <div class="logic-layout">
                <div class="logic-grid-wrap">
                    <table class="logic-table" id="logic-table">
                        <thead>
                            <tr>
                                <th class="logic-corner"></th>
                                ${cols.map(c => `<th class="logic-col-head">${c}</th>`).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            ${rows.map(row => `
                                <tr>
                                    <th class="logic-row-head">${row}</th>
                                    ${cols.map(col => `
                                        <td class="logic-cell" data-row="${row}" data-col="${col}"
                                            id="lc-${this._cellId(row, col)}">
                                            <span class="logic-mark"></span>
                                        </td>
                                    `).join('')}
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                    <div class="logic-result" id="logic-result"></div>
                </div>

                <div class="logic-clue-panel">
                    <div class="logic-clue-title">Clues</div>
                    <ol class="logic-clue-list">
                        ${this.clues.map(c => `<li class="logic-clue">${c.text}</li>`).join('')}
                    </ol>
                </div>
            </div>
        `;

        this._attachEvents();
    }

    _cellId(row, col) {
        return `${row}§${col}`.replace(/\s+/g, '_');
    }

    _attachEvents() {
        const table = document.getElementById('logic-table');
        if (!table) return;
        table.querySelectorAll('.logic-cell').forEach(cell => {
            cell.addEventListener('click', () => {
                if (this.isComplete) return;
                const row = cell.dataset.row;
                const col = cell.dataset.col;
                const key = `${row}§${col}`;
                const current = this.marks[key] || '';
                // Cycle: blank → yes → no → blank
                this.marks[key] = current === '' ? 'yes'
                    : current === 'yes' ? 'no'
                        : '';
                this._updateCell(cell, this.marks[key]);
                this._autoExclude(row, col, this.marks[key]);
                this._checkComplete();
            });
        });
    }

    _updateCell(cell, mark) {
        const span = cell.querySelector('.logic-mark');
        cell.classList.remove('mark-yes', 'mark-no');
        if (mark === 'yes') {
            cell.classList.add('mark-yes');
            if (span) span.textContent = '✓';
        } else if (mark === 'no') {
            cell.classList.add('mark-no');
            if (span) span.textContent = '✗';
        } else {
            if (span) span.textContent = '';
        }
    }

    /** When a row gets a ✓, auto-mark all other cols in that row as ✗ (and vice-versa). */
    _autoExclude(row, col, mark) {
        if (mark !== 'yes') return;
        const [catRow, catCol] = this.categories;
        const cols = this.items[catCol] || [];

        // Exclude other cols in same row
        cols.forEach(c => {
            if (c === col) return;
            const key = `${row}§${c}`;
            if ((this.marks[key] || '') === '') {
                this.marks[key] = 'no';
                const cell = document.getElementById(`lc-${this._cellId(row, c)}`);
                if (cell) this._updateCell(cell, 'no');
            }
        });

        // Exclude other rows in same col
        const rows = this.items[catRow] || [];
        rows.forEach(r => {
            if (r === row) return;
            const key = `${r}§${col}`;
            if ((this.marks[key] || '') === '') {
                this.marks[key] = 'no';
                const cell = document.getElementById(`lc-${this._cellId(r, col)}`);
                if (cell) this._updateCell(cell, 'no');
            }
        });
    }

    _checkComplete() {
        const [catRow, catCol] = this.categories;
        const rows = this.items[catRow] || [];
        const cols = this.items[catCol] || [];

        // Check if every row has exactly one ✓
        const assignment = {};
        for (const row of rows) {
            const yes = cols.filter(col => this.marks[`${row}§${col}`] === 'yes');
            if (yes.length !== 1) return;   // not done yet
            assignment[row] = yes[0];
        }

        // Fully filled — validate against solution
        this.isComplete = true;
        const correct = rows.every(row => assignment[row] === this.solution[row]);
        const resultEl = document.getElementById('logic-result');

        if (correct) {
            if (resultEl) resultEl.innerHTML =
                '<span class="logic-win">🎉 Correct! All deductions are right.</span>';
            this.container.dispatchEvent(new CustomEvent('logic:correct', { bubbles: true }));
        } else {
            if (resultEl) resultEl.innerHTML =
                '<span class="logic-error">✗ Some deductions are incorrect. Try again!</span>';
            this.isComplete = false;  // allow corrections
            this.container.dispatchEvent(new CustomEvent('logic:error', { bubbles: true }));
        }
    }

    /** Reset all marks. */
    reset() {
        this.marks = {};
        this.isComplete = false;
        this._render();
    }
}
