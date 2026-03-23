/* ─────────────────────────────────────────────────────
   Puzzler — Player Analytics Dashboard
   Fetches real data from /api/player/* and renders:
     · Animated skill meter
     · Canvas skill progression chart
     · Session history feed
     · Weakness pills panel
───────────────────────────────────────────────────── */

const BAND_LABELS = {
    beginner: { label: 'Beginner', color: '#6366f1' },
    easy: { label: 'Easy', color: '#22c55e' },
    medium: { label: 'Medium', color: '#f59e0b' },
    hard: { label: 'Hard', color: '#ef4444' },
    expert: { label: 'Expert', color: '#a855f7' },
};

function bandFromScore(score) {
    if (score < 25) return 'beginner';
    if (score < 50) return 'easy';
    if (score < 70) return 'medium';
    if (score < 85) return 'hard';
    return 'expert';
}

/* ── Entry point ─────────────────────────────────────── */
async function initDashboard() {
    const user = getCurrentUser();
    if (!user) {
        // Show auth prompt, hide stats
        const authPrompt = $('auth-prompt');
        const statsGrid = document.querySelector('.stats-grid');
        if (authPrompt) authPrompt.classList.remove('hidden');
        if (statsGrid) statsGrid.classList.add('hidden');
        return;
    }

    // Hide auth prompt, show content
    const authPrompt = $('auth-prompt');
    if (authPrompt) authPrompt.classList.add('hidden');

    // Fetch all data in parallel
    const [profile, historyData, weeknesses, sessions] = await Promise.allSettled([
        apiGetProfile(user.id),
        apiGetSkillHistory(user.id),
        apiGetWeaknesses(user.id),
        apiGetHistory(user.id),
    ]);

    if (profile.status === 'fulfilled') renderProfile(profile.value);
    if (historyData.status === 'fulfilled') renderSkillChart(historyData.value);
    if (weeknesses.status === 'fulfilled') renderWeaknessPanel(weeknesses.value);
    if (sessions.status === 'fulfilled') renderSessionHistory(sessions.value);
}

/* ── Profile stats ───────────────────────────────────── */
function renderProfile(profile) {
    // Stat cards
    const skillEl = $('stat-skill');
    const solvedEl = $('stat-solved');
    const avgTimeEl = $('stat-avg-time');
    const streakEl = $('streak-count');

    if (skillEl) skillEl.textContent = profile.current_skill_score.toFixed(1);
    if (solvedEl) solvedEl.textContent = profile.sessions_completed;
    if (avgTimeEl && profile.average_time_seconds) {
        avgTimeEl.textContent = formatTime(Math.round(profile.average_time_seconds));
    } else if (avgTimeEl) {
        avgTimeEl.textContent = '—';
    }
    if (streakEl) streakEl.textContent = profile.streak_days;

    // Animated skill meter
    renderSkillMeter(profile.current_skill_score);
}

/* ── Animated skill meter ────────────────────────────── */
function renderSkillMeter(score) {
    const container = $('skill-meter');
    if (!container) return;

    const band = bandFromScore(score);
    const info = BAND_LABELS[band] || BAND_LABELS.medium;
    const pct = Math.min(100, Math.max(0, score));

    container.innerHTML = `
        <div class="skill-meter-header">
            <span class="skill-meter-label">Skill Level</span>
            <span class="skill-meter-band" style="color:${info.color}">${info.label}</span>
        </div>
        <div class="skill-meter-track">
            <div class="skill-meter-fill" id="skill-meter-fill"
                 style="width:0%; background:${info.color}">
            </div>
        </div>
        <div class="skill-meter-score">${score.toFixed(1)} / 100</div>
    `;

    // Animate fill after paint
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            const fill = $('skill-meter-fill');
            if (fill) fill.style.width = `${pct}%`;
        });
    });
}

/* ── Skill chart (Canvas line chart) ─────────────────── */
function renderSkillChart(data) {
    const container = $('skill-chart');
    if (!container) return;

    const points = data.points || [];
    if (points.length === 0) {
        container.innerHTML = '<p class="chart-empty-msg">Play your first puzzle to start tracking your skill curve.</p>';
        return;
    }

    // Build canvas
    container.innerHTML = '<canvas id="skill-canvas" style="width:100%;height:180px;"></canvas>';
    const canvas = document.getElementById('skill-canvas');
    const W = canvas.offsetWidth || container.offsetWidth || 600;
    const H = 180;
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext('2d');

    const PAD = { top: 12, right: 16, bottom: 32, left: 40 };
    const chartW = W - PAD.left - PAD.right;
    const chartH = H - PAD.top - PAD.bottom;

    const scores = points.map(p => p.skill_score);
    const minVal = Math.max(0, Math.min(...scores) - 5);
    const maxVal = Math.min(100, Math.max(...scores) + 5);
    const range = maxVal - minVal || 1;

    const toX = (i) => PAD.left + (i / (points.length - 1 || 1)) * chartW;
    const toY = (v) => PAD.top + chartH - ((v - minVal) / range) * chartH;

    // Y-grid lines
    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.lineWidth = 1;
    [25, 50, 75, 100].forEach(y => {
        if (y >= minVal && y <= maxVal) {
            const cy = toY(y);
            ctx.beginPath(); ctx.moveTo(PAD.left, cy); ctx.lineTo(PAD.left + chartW, cy);
            ctx.stroke();
            ctx.fillStyle = 'rgba(255,255,255,0.35)';
            ctx.font = '10px Inter,sans-serif';
            ctx.fillText(y, PAD.left - 28, cy + 4);
        }
    });

    // Gradient fill under the line
    const grad = ctx.createLinearGradient(0, PAD.top, 0, PAD.top + chartH);
    grad.addColorStop(0, 'rgba(139,92,246,0.35)');
    grad.addColorStop(1, 'rgba(139,92,246,0.0)');
    ctx.beginPath();
    ctx.moveTo(toX(0), toY(scores[0]));
    points.forEach((p, i) => { if (i > 0) ctx.lineTo(toX(i), toY(p.skill_score)); });
    ctx.lineTo(toX(points.length - 1), PAD.top + chartH);
    ctx.lineTo(toX(0), PAD.top + chartH);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // Line
    ctx.beginPath();
    ctx.strokeStyle = '#8b5cf6';
    ctx.lineWidth = 2.5;
    ctx.lineJoin = 'round';
    points.forEach((p, i) => {
        const x = toX(i); const y = toY(p.skill_score);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Data points
    points.forEach((p, i) => {
        const x = toX(i); const y = toY(p.skill_score);
        ctx.beginPath();
        ctx.arc(x, y, 3.5, 0, Math.PI * 2);
        ctx.fillStyle = '#8b5cf6';
        ctx.fill();
        ctx.strokeStyle = 'var(--surface-1, #1a1a2e)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
    });

    // X-axis: first and last timestamp
    ctx.fillStyle = 'rgba(255,255,255,0.35)';
    ctx.font = '10px Inter,sans-serif';
    const fmt = (iso) => new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    ctx.fillText(fmt(points[0].recorded_at), PAD.left, H - 8);
    if (points.length > 1) {
        const lastLabel = fmt(points[points.length - 1].recorded_at);
        ctx.fillText(lastLabel, PAD.left + chartW - ctx.measureText(lastLabel).width, H - 8);
    }
}

/* ── Session history feed ────────────────────────────── */
function renderSessionHistory(sessions) {
    const container = $('history-feed');
    if (!container) return;

    if (!sessions || sessions.length === 0) {
        container.innerHTML = '<p class="chart-empty-msg">No sessions yet. Play a puzzle!</p>';
        return;
    }

    const rows = sessions.slice(0, 10).map(s => {
        const band = s.difficulty_band || 'medium';
        const info = BAND_LABELS[band] || BAND_LABELS.medium;
        const outcome = s.is_complete
            ? '<span class="hist-outcome win">✓ Solved</span>'
            : '<span class="hist-outcome loss">✗ Incomplete</span>';
        const time = s.time_seconds ? formatTime(s.time_seconds) : '—';
        const delta = (s.skill_score_before != null && s.skill_score_after != null)
            ? (() => {
                const d = (s.skill_score_after - s.skill_score_before).toFixed(1);
                const sign = d >= 0 ? '+' : '';
                const cls = d >= 0 ? 'delta-up' : 'delta-down';
                return `<span class="hist-delta ${cls}">${sign}${d}</span>`;
            })()
            : '';
        return `
            <div class="hist-row">
                <span class="hist-type" style="color:${info.color}">${s.puzzle_type || 'sudoku'}</span>
                <span class="hist-band" style="background:${info.color}22;color:${info.color}">${band}</span>
                <span class="hist-time">⏱ ${time}</span>
                <span class="hist-errors">✕ ${s.error_count}</span>
                ${outcome}
                ${delta}
            </div>`;
    }).join('');

    container.innerHTML = `<div class="hist-list">${rows}</div>`;
}

/* ── Weakness panel ──────────────────────────────────── */
function renderWeaknessPanel(report) {
    const container = $('weakness-grid');
    if (!container) return;

    const domains = report.weak_domains || [];
    if (domains.length === 0) {
        container.innerHTML = `
            <div class="weakness-pill">${report.recommended_focus || 'Keep playing to build your weakness profile!'}</div>`;
        return;
    }

    const pills = domains.map(d =>
        `<div class="weakness-pill active-weak">Cell ${d}</div>`
    ).join('');
    const tip = `<div class="weakness-tip">💡 ${report.recommended_focus}</div>`;
    container.innerHTML = pills + tip;
}
