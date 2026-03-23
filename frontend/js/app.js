/* ─────────────────────────────────────────────────────
   Puzzler — Main App
   Client-side router, state management, timer,
   auth modal, page navigation, and toast system.
───────────────────────────────────────────────────── */

/* ── State ──────────────────────────────────────────── */
const state = {
    currentPage: 'home',
    sessionId: null,
    timerInterval: null,
    elapsedSeconds: 0,
    hintCount: 0,
    board: null,
    currentDifficultyBand: 'medium',
};

/* ── DOM refs ─────────────────────────────────────────── */
const $ = id => document.getElementById(id);

/* ── Toast helper ─────────────────────────────────────── */
function showToast(message, type = 'default') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    $('toast-container').appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

/* ── Page router ──────────────────────────────────────── */
function navigateTo(pageId) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const page = $(`page-${pageId}`);
    if (page) {
        page.classList.add('active');
        state.currentPage = pageId;
    }

    // Update nav active link
    document.querySelectorAll('.nav-link').forEach(l => {
        l.classList.toggle('active', l.dataset.page === pageId);
    });

    // Page-specific init
    if (pageId === 'play') initPlayPage();
    if (pageId === 'dashboard') initDashboardPage();
}

/* ── Play page ────────────────────────────────────────── */
async function initPlayPage() {
    // Set date subtitle
    const now = new Date();
    $('play-date').textContent = now.toLocaleDateString('en-US', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
    });

    // Fetch a real puzzle from the API (only once per session)
    if (!state.board) {
        await loadNewPuzzle('medium');
    }

    // Start the timer
    startTimer();

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const type = btn.dataset.type;
            $('sudoku-board-wrapper').classList.toggle('hidden', type !== 'sudoku');
            $('word-board-wrapper').classList.toggle('hidden', type !== 'word');
            $('logic-board-wrapper').classList.toggle('hidden', type !== 'logic');
        });
    });

    // Hint button
    $('btn-hint').addEventListener('click', () => {
        if (!state.board || state.board.isComplete) return;
        state.board.showHint();
        state.hintCount++;
        showToast('💡 Hint used! -10 skill points', 'default');
    });

    // Reset button
    $('btn-reset').addEventListener('click', () => {
        if (!state.board) return;
        state.board.reset();
        state.hintCount = 0;
        resetTimer();
        showToast('Board reset ↺');
    });

    // New puzzle button (if present)
    const btnNew = $('btn-new-puzzle');
    if (btnNew) {
        btnNew.addEventListener('click', async () => {
            state.board = null;
            resetTimer();
            stopTimer();
            const band = state.currentDifficultyBand || 'medium';
            await loadNewPuzzle(band);
            startTimer();
        });
    }

    // Listen for sudoku events — wire to session API (fire-and-forget)
    document.addEventListener('sudoku:error', (e) => {
        if (state.sessionId) {
            const { row, col, value } = e.detail || {};
            const cellId = (row != null && col != null) ? `${row},${col}` : null;
            apiLogEvent(state.sessionId, 'error', cellId, String(value ?? '')).catch(() => { });
        }
    });

    document.addEventListener('sudoku:hint', (e) => {
        if (state.sessionId) {
            const { row, col } = e.detail || {};
            const cellId = (row != null && col != null) ? `${row},${col}` : null;
            apiLogEvent(state.sessionId, 'hint', cellId).catch(() => { });
        }
    });

    document.addEventListener('sudoku:complete', async () => {
        stopTimer();
        const time = state.elapsedSeconds;
        $('game-status').innerHTML = '<span class="status-pill" style="background:var(--accent-green-bg);color:#3a7a36;border-color:var(--accent-green)">✓ Solved!</span>';
        showToast(`🎉 Solved in ${formatTime(time)}!`, 'success');

        // Close the session and update skill score
        if (state.sessionId) {
            try {
                const result = await apiCompleteSession(state.sessionId, time, true);
                if (result?.skill_score_after != null) {
                    const delta = (result.skill_score_after - result.skill_score_before).toFixed(1);
                    const sign = delta >= 0 ? '+' : '';
                    showToast(`⭐ Skill: ${result.skill_score_after.toFixed(1)} (${sign}${delta})`, 'success');
                }
            } catch (err) {
                console.warn('Could not record session completion:', err.message);
            }
            state.sessionId = null;
        }
    });
}

/**
 * Fetch a puzzle from the API and initialise the SudokuBoard.
 * Falls back to the offline DEMO_PUZZLE if the API is unreachable.
 * @param {string} band - difficulty band (beginner|easy|medium|hard|expert)
 */
async function loadNewPuzzle(band = 'medium') {
    state.currentDifficultyBand = band;

    // Show loading state
    const boardEl = $('sudoku-board');
    if (boardEl) {
        boardEl.innerHTML = '<div class="board-loading">Generating puzzle…</div>';
    }

    try {
        const data = await apiGeneratePuzzle('sudoku', band);
        const puzzle2D = flatTo2D(data.data.grid);
        const solution2D = flatTo2D(data.solution.grid);
        const meta = {
            difficulty_band: data.difficulty_band,
            difficulty_score: data.difficulty_score,
            clue_count: data.data.clue_count,
            puzzle_id: data.id,
        };
        state.board = new SudokuBoard('sudoku-board', puzzle2D, solution2D, meta);
        state.board.renderMeta();
        showToast(`New ${band} Sudoku loaded ✨`, 'success');

        // Start a session for logged-in users (fire-and-forget if no user)
        const user = getCurrentUser();
        if (user) {
            try {
                const sess = await apiStartSession(user.id, data.id);
                state.sessionId = sess?.id ?? null;
            } catch (e) {
                console.warn('Could not start session:', e.message);
                state.sessionId = null;
            }
        }
    } catch (err) {
        console.warn('API unavailable — falling back to demo puzzle:', err.message);
        state.board = new SudokuBoard('sudoku-board');
        state.sessionId = null;
        showToast('Playing in offline mode 📵', 'default');
    }
}

/* ── Timer ───────────────────────────────────────────── */
function formatTime(s) {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, '0')}`;
}

function startTimer() {
    if (state.timerInterval) return; // already running
    state.timerInterval = setInterval(() => {
        state.elapsedSeconds++;
        $('game-timer').textContent = formatTime(state.elapsedSeconds);
    }, 1000);
}

function stopTimer() {
    clearInterval(state.timerInterval);
    state.timerInterval = null;
}

function resetTimer() {
    stopTimer();
    state.elapsedSeconds = 0;
    $('game-timer').textContent = '0:00';
    startTimer();
}

/* ── Dashboard page ──────────────────────────────────── */
async function initDashboardPage() {
    // Delegate to the full analytics renderer in dashboard.js
    await initDashboard();
}

/* ── Auth modal ──────────────────────────────────────── */
function openModal(tab = 'login') {
    $('auth-modal').classList.remove('hidden');
    switchModalTab(tab);
}
function closeModal() {
    $('auth-modal').classList.add('hidden');
}
function switchModalTab(tab) {
    $('login-form').classList.toggle('hidden', tab !== 'login');
    $('register-form').classList.toggle('hidden', tab !== 'register');
    $('tab-login-modal').classList.toggle('active', tab === 'login');
    $('tab-register-modal').classList.toggle('active', tab === 'register');
}

function updateNavForAuth() {
    const user = getCurrentUser();
    const actions = $('nav-actions');
    if (user) {
        actions.innerHTML = `
      <span style="font-size:0.85rem;color:var(--text-muted)">Hi, <strong>${user.username}</strong></span>
      <button class="btn btn-ghost" id="btn-logout">Log out</button>
    `;
        $('btn-logout').addEventListener('click', () => {
            clearAuth();
            updateNavForAuth();
            navigateTo('home');
            showToast('Logged out.');
        });
    } else {
        actions.innerHTML = `
      <button class="btn btn-ghost" id="btn-login">Log in</button>
      <button class="btn btn-primary" id="btn-register">Get Started</button>
    `;
        $('btn-login').addEventListener('click', () => openModal('login'));
        $('btn-register').addEventListener('click', () => openModal('register'));
    }
}

/* ── Auth form handlers ──────────────────────────────── */
async function handleLogin(e) {
    e.preventDefault();
    const username = $('login-username').value.trim();
    const password = $('login-password').value;
    const errEl = $('login-error');
    errEl.classList.add('hidden');
    try {
        await apiLogin(username, password);
        closeModal();
        updateNavForAuth();
        showToast('Welcome back! 👋', 'success');
        navigateTo('play');
    } catch (err) {
        errEl.textContent = err.message;
        errEl.classList.remove('hidden');
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const username = $('reg-username').value.trim();
    const email = $('reg-email').value.trim();
    const password = $('reg-password').value;
    const errEl = $('reg-error');
    errEl.classList.add('hidden');
    try {
        await apiRegister(username, email, password);
        closeModal();
        updateNavForAuth();
        showToast('Account created! Ready to puzzle 🎉', 'success');
        navigateTo('play');
    } catch (err) {
        errEl.textContent = err.message;
        errEl.classList.remove('hidden');
    }
}

/* ── DOMContentLoaded ─────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
    // Hero sudoku preview
    renderHeroSudoku();

    // Nav links
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            navigateTo(link.dataset.page);
        });
    });

    $('nav-home').addEventListener('click', (e) => {
        e.preventDefault();
        navigateTo('home');
    });

    // Hero CTAs
    $('btn-play-now').addEventListener('click', () => navigateTo('play'));
    $('btn-learn-more').addEventListener('click', () => {
        $('how-it-works').scrollIntoView({ behavior: 'smooth' });
    });

    // Modal controls
    $('modal-close').addEventListener('click', closeModal);
    $('auth-modal').addEventListener('click', (e) => {
        if (e.target === $('auth-modal')) closeModal();
    });
    $('tab-login-modal').addEventListener('click', () => switchModalTab('login'));
    $('tab-register-modal').addEventListener('click', () => switchModalTab('register'));

    // Auth forms
    $('login-form').addEventListener('submit', handleLogin);
    $('register-form').addEventListener('submit', handleRegister);

    // Dashboard auth prompt
    $('btn-signup-dashboard').addEventListener('click', () => openModal('register'));

    // Auth state
    updateNavForAuth();

    // Boot page
    navigateTo('home');
});
