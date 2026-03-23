/* ─────────────────────────────────────────────────────
   Puzzler — API Client
   Thin wrapper around fetch() for all backend calls.
───────────────────────────────────────────────────── */

const API_BASE = 'http://localhost:8000/api';

/** Read the stored JWT token. */
function getToken() {
    return localStorage.getItem('puzzler_token');
}

/** Store token + user after login/register. */
function storeAuth(tokenData) {
    localStorage.setItem('puzzler_token', tokenData.access_token);
    localStorage.setItem('puzzler_user', JSON.stringify(tokenData.user));
}

/** Clear auth state on logout. */
function clearAuth() {
    localStorage.removeItem('puzzler_token');
    localStorage.removeItem('puzzler_user');
}

/** Return the current user object or null. */
function getCurrentUser() {
    const raw = localStorage.getItem('puzzler_user');
    return raw ? JSON.parse(raw) : null;
}

/** Base fetch that attaches auth header and parses JSON. */
async function apiFetch(path, options = {}) {
    const token = getToken();
    const headers = {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {}),
    };
    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Request failed');
    }
    if (res.status === 204) return null;
    return res.json();
}

/* ── Auth ─────────────────────────────────────────── */
async function apiRegister(username, email, password) {
    const data = await apiFetch('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ username, email, password }),
    });
    storeAuth(data);
    return data;
}

async function apiLogin(username, password) {
    const data = await apiFetch('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
    });
    storeAuth(data);
    return data;
}

/* ── Puzzles ──────────────────────────────────────── */
async function apiGetDailyPuzzle() {
    return apiFetch('/puzzle/daily');
}

async function apiGetNextPuzzle(userId) {
    return apiFetch(`/puzzle/next?user_id=${userId}`);
}

async function apiGeneratePuzzle(type = 'sudoku', difficulty_band = 'medium') {
    return apiFetch('/puzzle/generate', {
        method: 'POST',
        body: JSON.stringify({ type, difficulty_band }),
    });
}

async function apiGetPuzzle(puzzleId) {
    return apiFetch(`/puzzle/${puzzleId}`);
}

/* ── Session ──────────────────────────────────────── */
async function apiStartSession(userId, puzzleId) {
    return apiFetch(`/session/start?user_id=${userId}`, {
        method: 'POST',
        body: JSON.stringify({ puzzle_id: puzzleId }),
    });
}

async function apiLogEvent(sessionId, eventType, cellId = null, value = null, extra = {}) {
    return apiFetch(`/session/${sessionId}/event`, {
        method: 'POST',
        body: JSON.stringify({ event_type: eventType, cell_id: cellId, value, extra }),
    });
}

async function apiCompleteSession(sessionId, timeSeconds, isCorrect) {
    return apiFetch(`/session/${sessionId}/complete`, {
        method: 'POST',
        body: JSON.stringify({ time_seconds: timeSeconds, is_correct: isCorrect }),
    });
}

/* ── Player ─────────────────────────────────────────── */
async function apiGetProfile(userId) {
    return apiFetch(`/player/profile?user_id=${userId}`);
}

async function apiGetWeaknesses(userId) {
    return apiFetch(`/player/weaknesses?user_id=${userId}`);
}

async function apiGetHistory(userId) {
    return apiFetch(`/player/history?user_id=${userId}`);
}

async function apiGetSkillHistory(userId, limit = 50) {
    return apiFetch(`/player/skill-history?user_id=${userId}&limit=${limit}`);
}

