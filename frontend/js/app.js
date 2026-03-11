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
function initPlayPage() {
    // Set date subtitle
    const now = new Date();
    $('play-date').textContent = now.toLocaleDateString('en-US', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
    });

    // Build the Sudoku board if not already built
    if (!state.board) {
        state.board = new SudokuBoard('sudoku-board');
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

    // Listen for sudoku events
    document.addEventListener('sudoku:error', (e) => {
        // Logged to session API on Day 5
        console.log('Error at', e.detail);
    });

    document.addEventListener('sudoku:hint', () => {
        console.log('Hint used');
    });

    document.addEventListener('sudoku:complete', () => {
        stopTimer();
        const time = state.elapsedSeconds;
        $('game-status').innerHTML = '<span class="status-pill" style="background:var(--accent-green-bg);color:#3a7a36;border-color:var(--accent-green)">✓ Solved!</span>';
        showToast(`🎉 Solved in ${formatTime(time)}!`, 'success');
    });
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
    const user = getCurrentUser();
    if (!user) {
        $('auth-prompt').classList.remove('hidden');
        return;
    }
    $('auth-prompt').classList.add('hidden');

    try {
        const profile = await apiGetProfile(user.id);
        $('stat-skill').textContent = Math.round(profile.current_skill_score);
        $('stat-solved').textContent = profile.sessions_completed;
        $('streak-count').textContent = profile.streak_days;
        if (profile.average_time_seconds) {
            $('stat-avg-time').textContent = formatTime(Math.round(profile.average_time_seconds));
        }
    } catch (e) {
        console.warn('Profile fetch failed:', e.message);
    }
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
