/**
 * Conversation Evaluation Benchmark — UI Application
 * Vanilla JS for API calls, dynamic rendering, and Chart.js integration.
 */

// ── State ──
let currentResult = null;
let activeTurnIndex = 0;
let radarChart = null;

// ── Initialization ──
document.addEventListener('DOMContentLoaded', async () => {
    addTurn('user');
    addTurn('assistant');
    await loadFacetStats();
});

async function loadFacetStats() {
    try {
        const resp = await fetch('/api/health');
        const data = await resp.json();
        document.getElementById('totalFacets').textContent = data.total_facets;
        document.getElementById('totalCategories').textContent = Object.keys(data.categories).length;
    } catch (e) {
        console.error('Failed to load stats:', e);
    }
}

// ── Turn Management ──
function addTurn(role = 'user') {
    const turnList = document.getElementById('turnList');
    const turnItem = document.createElement('div');
    turnItem.className = 'turn-item';
    turnItem.innerHTML = `
        <div class="turn-role">
            <select>
                <option value="user" ${role === 'user' ? 'selected' : ''}>User</option>
                <option value="assistant" ${role === 'assistant' ? 'selected' : ''}>Assistant</option>
            </select>
        </div>
        <div class="turn-content">
            <textarea placeholder="Enter message content..." rows="2"></textarea>
        </div>
        <button class="turn-remove" onclick="removeTurn(this)" title="Remove turn">✕</button>
    `;
    turnList.appendChild(turnItem);
    turnItem.querySelector('textarea').focus();
}

function removeTurn(btn) {
    const turnList = document.getElementById('turnList');
    if (turnList.children.length > 1) {
        btn.closest('.turn-item').remove();
    }
}

function getConversation() {
    const turns = [];
    document.querySelectorAll('.turn-item').forEach(item => {
        const role = item.querySelector('select').value;
        const content = item.querySelector('textarea').value.trim();
        if (content) turns.push({ role, content });
    });
    return turns;
}

// ── Evaluation ──
async function runEvaluation() {
    const turns = getConversation();
    if (turns.length === 0) return showToast('Please add conversation turns first', 'error');
    await _evaluate('/api/evaluate', turns);
}

async function _evaluate(endpoint, turns) {
    const btn = document.getElementById('evalBtn');
    const progressBar = document.getElementById('progressBar');

    btn.classList.add('loading');
    btn.disabled = true;
    progressBar.classList.add('visible');

    try {
        const resp = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                conversation: { turns },
            }),
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || 'Evaluation failed');
        }

        currentResult = await resp.json();
        activeTurnIndex = 0;
        renderResults(currentResult);
        showToast('Evaluation complete!', 'success');

    } catch (e) {
        console.error('Evaluation error:', e);
        showToast(e.message, 'error');
    } finally {
        btn.classList.remove('loading');
        btn.disabled = false;
        progressBar.classList.remove('visible');
    }
}

// ── Render Results ──
function renderResults(result) {
    const panel = document.getElementById('resultsPanel');
    panel.classList.add('visible');

    renderSummaryGrid(result.category_averages);
    renderRadarChart(result.category_averages);
    renderTurnTabs(result);
    renderScores(result.turn_evaluations[activeTurnIndex]);

    // Smooth scroll to results
    panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderSummaryGrid(averages) {
    const grid = document.getElementById('summaryGrid');
    grid.innerHTML = Object.entries(averages)
        .sort((a, b) => b[1] - a[1])
        .map(([cat, avg]) => `
            <div class="summary-card">
                <div class="cat-label">${formatCategory(cat)}</div>
                <div class="cat-score" style="color: ${getScoreColor(avg)}">${avg.toFixed(1)}</div>
            </div>
        `).join('');
}

function renderRadarChart(averages) {
    const ctx = document.getElementById('radarChart').getContext('2d');
    const labels = Object.keys(averages).map(formatCategory);
    const values = Object.values(averages);

    if (radarChart) radarChart.destroy();

    radarChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels,
            datasets: [{
                label: 'Average Score',
                data: values,
                backgroundColor: 'rgba(99, 102, 241, 0.15)',
                borderColor: 'rgba(99, 102, 241, 0.8)',
                borderWidth: 2,
                pointBackgroundColor: 'rgba(99, 102, 241, 1)',
                pointRadius: 4,
                pointHoverRadius: 6,
            }]
        },
        options: {
            responsive: true,
            scales: {
                r: {
                    beginAtZero: true,
                    max: 5,
                    ticks: {
                        stepSize: 1,
                        color: '#64748b',
                        backdropColor: 'transparent',
                        font: { size: 10 }
                    },
                    grid: { color: 'rgba(99, 102, 241, 0.1)' },
                    angleLines: { color: 'rgba(99, 102, 241, 0.1)' },
                    pointLabels: {
                        color: '#94a3b8',
                        font: { size: 11, family: 'Inter' }
                    }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

function renderTurnTabs(result) {
    const tabs = document.getElementById('turnTabs');
    tabs.innerHTML = result.turn_evaluations.map((te, i) => `
        <button class="turn-tab ${i === activeTurnIndex ? 'active' : ''}"
                onclick="switchTurn(${i})">
            Turn ${i + 1} (${te.role})
        </button>
    `).join('');
}

function switchTurn(index) {
    activeTurnIndex = index;
    renderTurnTabs(currentResult);
    renderScores(currentResult.turn_evaluations[index]);
}

function renderScores(turnEval) {
    const container = document.getElementById('scoresContainer');

    // Group by category
    const byCategory = {};
    turnEval.facet_scores.forEach(fs => {
        if (!byCategory[fs.category]) byCategory[fs.category] = [];
        byCategory[fs.category].push(fs);
    });

    // Sort categories
    const sortedCats = Object.keys(byCategory).sort();

    container.innerHTML = sortedCats.map(cat => {
        const facets = byCategory[cat];
        const avgScore = facets.reduce((s, f) => s + f.score, 0) / facets.length;

        return `
            <div class="category-section" onclick="toggleCategory(this, event)">
                <div class="category-header">
                    <span class="cat-name">
                        ${getCategoryIcon(cat)} ${formatCategory(cat)}
                        <span style="color: var(--text-muted); font-weight: 400; font-size: 0.8rem;">
                            (${facets.length} facets)
                        </span>
                    </span>
                    <div class="cat-avg">
                        <span class="avg-score score-${Math.round(avgScore)}">${avgScore.toFixed(1)}</span>
                        <span class="chevron">▼</span>
                    </div>
                </div>
                <div class="category-body">
                    ${facets.map(f => renderFacetRow(f)).join('')}
                </div>
            </div>
        `;
    }).join('');
}

function renderFacetRow(fs) {
    const confColor = fs.confidence > 0.7 ? 'var(--accent-4)' : fs.confidence > 0.4 ? 'var(--accent-5)' : 'var(--score-1)';
    return `
        <div class="facet-row">
            <span class="facet-name">${fs.facet_name}</span>
            <span class="score-badge score-${fs.score}">${fs.score}</span>
            <div>
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width: ${fs.confidence * 100}%; background: ${confColor};"></div>
                </div>
                <div class="confidence-label">${(fs.confidence * 100).toFixed(0)}% conf</div>
            </div>
            <span class="facet-reasoning">${fs.reasoning || '—'}</span>
        </div>
    `;
}

// ── Helpers ──
function formatCategory(cat) {
    return cat.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function getScoreColor(score) {
    if (score >= 4) return 'var(--score-5)';
    if (score >= 3) return 'var(--score-4)';
    if (score >= 2.5) return 'var(--score-3)';
    if (score >= 1.5) return 'var(--score-2)';
    return 'var(--score-1)';
}

function getCategoryIcon(cat) {
    return '';
}

function toggleCategory(el, e) {
    // Don't toggle if clicking inside the body
    if (e.target.closest('.category-body')) return;
    el.classList.toggle('expanded');
}

function expandAll() {
    const sections = document.querySelectorAll('.category-section');
    const anyExpanded = [...sections].some(s => s.classList.contains('expanded'));
    sections.forEach(s => {
        if (anyExpanded) s.classList.remove('expanded');
        else s.classList.add('expanded');
    });
}

function exportJSON() {
    if (!currentResult) return showToast('No results to export', 'error');
    const blob = new Blob([JSON.stringify(currentResult, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `evaluation_${currentResult.conversation_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('JSON exported!', 'success');
}

function showToast(msg, type = '') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}
