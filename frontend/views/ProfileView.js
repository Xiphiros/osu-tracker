import { getReplays, getPlayerStats } from '../services/api.js';
import { createReplayCard } from '../components/ReplayCard.js';
import { getModsFromInt } from '../utils/mods.js';

let allScores = [];
let viewInitialized = false;
let profileChart = null;
let currentChartType = 'pp';
const activeModFilters = new Set();

// --- Helper Functions ---
function calculateAccuracy(replay) {
    const totalHits = replay.num_300s + replay.num_100s + replay.num_50s + replay.num_misses;
    if (totalHits === 0) return 0;
    return ((replay.num_300s * 300 + replay.num_100s * 100 + replay.num_50s * 50) / (totalHits * 300)) * 100;
}

function renderProfileChart(scores, type) {
    const chartWrapper = document.getElementById('chart-wrapper');
    if (!chartWrapper) return;
    chartWrapper.style.display = scores.length > 0 ? 'block' : 'none';

    if (profileChart) {
        profileChart.destroy();
    }
    if (scores.length === 0) return;

    const ctx = document.getElementById('profile-chart').getContext('2d');
    const chartLabel = type === 'pp' ? 'PP Over Time' : 'Star Rating Over Time';
    const chartData = scores.map(s => (type === 'pp' ? s.pp : s.stars) || 0);
    const pointColor = type === 'pp' ? 'rgba(0, 170, 255, 0.8)' : 'rgba(255, 204, 34, 0.8)';
    const lineColor = type === 'pp' ? 'rgba(0, 170, 255, 0.5)' : 'rgba(255, 204, 34, 0.5)';

    profileChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: scores.map(s => new Date(s.played_at)),
            datasets: [{
                label: chartLabel,
                data: chartData,
                backgroundColor: pointColor,
                borderColor: lineColor,
                borderWidth: 2,
                pointRadius: 3,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'month',
                        tooltipFormat: 'MMM yyyy',
                        displayFormats: { month: 'MMM yyyy' }
                    },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    ticks: { color: '#ccc' }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    ticks: { color: '#ccc' }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: context => new Date(context[0].parsed.x).toLocaleDateString(),
                        label: context => `${type.toUpperCase()}: ${context.parsed.y.toFixed(2)}`
                    }
                }
            }
        }
    });
}

// --- Main View and Logic ---
function applyFiltersAndRender(viewElement) {
    const replaysContainer = viewElement.querySelector('#profile-replays-container');
    const analyticsContainer = viewElement.querySelector('#profile-analytics');
    replaysContainer.innerHTML = '';
    analyticsContainer.innerHTML = '';

    const sortValue = viewElement.querySelector('#sort-select').value;
    const minAcc = parseFloat(viewElement.querySelector('#acc-filter-min').value) || 0;
    const maxAcc = parseFloat(viewElement.querySelector('#acc-filter-max').value) || 100;
    const minStars = parseFloat(viewElement.querySelector('#stars-filter-min').value) || 0;
    const minBpm = parseFloat(viewElement.querySelector('#bpm-filter-min').value) || 0;
    const maxBpm = parseFloat(viewElement.querySelector('#bpm-filter-max').value) || Infinity;
    const exactMatch = viewElement.querySelector('#exact-mod-match-toggle').checked;

    let filteredScores = allScores;

    if (activeModFilters.size > 0) {
        filteredScores = filteredScores.filter(replay => {
            const replayMods = new Set(getModsFromInt(replay.mods_used));
            if (exactMatch) {
                if (replayMods.size !== activeModFilters.size) return false;
            }
            return [...activeModFilters].every(mod => replayMods.has(mod));
        });
    }

    filteredScores = filteredScores.filter(replay => {
        const acc = calculateAccuracy(replay);
        const stars = replay.stars || 0;
        const bpm = replay.beatmap?.bpm || 0;
        
        return acc >= minAcc && acc <= maxAcc &&
               stars >= minStars &&
               bpm >= minBpm && bpm <= maxBpm;
    });

    if (filteredScores.length > 0) {
        const scoresForAnalytics = [...filteredScores].sort((a, b) => (b.stars || 0) - (a.stars || 0)).slice(0, 100);
        const totalStars = scoresForAnalytics.reduce((sum, score) => sum + (score.stars || 0), 0);
        const avgStars = scoresForAnalytics.length > 0 ? (totalStars / scoresForAnalytics.length).toFixed(2) : '0.00';
        
        analyticsContainer.innerHTML = `
            <div class="stat-item">
                <span class="stat-label">Average Star Rating (Top ${scoresForAnalytics.length} Plays)</span>
                <span class="stat-value">★ ${avgStars}</span>
            </div>
        `;
    }

    const scoresForChart = [...filteredScores].sort((a, b) => new Date(a.played_at) - new Date(b.played_at));
    renderProfileChart(scoresForChart, currentChartType);

    filteredScores.sort((a, b) => {
        switch (sortValue) {
            case 'pp': return (b.pp || 0) - (a.pp || 0);
            case 'score': return b.total_score - a.total_score;
            case 'date': return new Date(b.played_at) - new Date(a.played_at);
            case 'stars': return (b.stars || 0) - (a.stars || 0);
            default: return (b.pp || 0) - (a.pp || 0);
        }
    });
    
    if (filteredScores.length > 0) {
        filteredScores.forEach(replay => replaysContainer.appendChild(createReplayCard(replay)));
    } else {
        replaysContainer.innerHTML = '<p>No scores match the current filters.</p>';
    }
     document.getElementById('status-message').textContent = `Displaying ${filteredScores.length} scores.`;
}

export function createProfileView() {
    const view = document.createElement('div');
    view.id = 'profile-view';
    view.className = 'view';
    view.innerHTML = `
        <div id="profile-header">
            <h2 id="profile-player-name"></h2>
            <div id="profile-stats" class="stats-container"></div>
            <div id="profile-analytics" class="stats-container"></div>
            <div class="profile-filters">
                <div id="mod-filter-container" class="mod-filter-container"></div>
                <select id="sort-select">
                    <option value="pp">Sort by: Highest PP</option>
                    <option value="score">Sort by: Highest Score</option>
                    <option value="date">Sort by: Most Recent</option>
                    <option value="stars">Sort by: Highest Stars</option>
                </select>
                <input type="number" id="acc-filter-min" min="0" max="100" step="0.1" placeholder="Min Acc %">
                <input type="number" id="acc-filter-max" min="0" max="100" step="0.1" placeholder="Max Acc %">
                <input type="number" id="stars-filter-min" min="0" step="0.1" placeholder="Min Stars ★">
                <input type="number" id="bpm-filter-min" min="0" step="1" placeholder="Min BPM">
                <input type="number" id="bpm-filter-max" min="0" step="1" placeholder="Max BPM">
                <div class="toggle-switch-container">
                    <label for="exact-mod-match-toggle" class="toggle-switch-label">Exact Match</label>
                    <label class="toggle-switch">
                        <input type="checkbox" id="exact-mod-match-toggle">
                        <span class="slider round"></span>
                    </label>
                </div>
            </div>
        </div>
        <div id="chart-section">
            <div class="chart-controls">
                <button id="chart-btn-pp" class="active">PP Graph</button>
                <button id="chart-btn-sr">SR Graph</button>
            </div>
            <div id="chart-wrapper" class="chart-wrapper">
                <canvas id="profile-chart"></canvas>
            </div>
        </div>
        <div id="profile-replays-container"></div>
    `;
    return view;
}

export async function loadProfile(viewElement, playerName) {
    if (!playerName) {
        viewElement.innerHTML = '<h2>Select a player to view their profile.</h2>';
        viewInitialized = false;
        return;
    }

    const nameHeader = viewElement.querySelector('#profile-player-name');
    const statsContainer = viewElement.querySelector('#profile-stats');
    const statusMessage = document.getElementById('status-message');
    const modContainer = viewElement.querySelector('#mod-filter-container');

    nameHeader.textContent = `${playerName}'s Profile`;
    statsContainer.innerHTML = 'Loading stats...';
    modContainer.innerHTML = ''; 
    activeModFilters.clear(); 
    statusMessage.textContent = `Loading ${playerName}'s profile...`;
    
    if (!viewInitialized) {
        viewElement.querySelectorAll('#sort-select, #acc-filter-min, #acc-filter-max, #stars-filter-min, #bpm-filter-min, #bpm-filter-max, #exact-mod-match-toggle').forEach(el => {
            el.addEventListener('input', () => applyFiltersAndRender(viewElement));
        });

        const ppBtn = viewElement.querySelector('#chart-btn-pp');
        const srBtn = viewElement.querySelector('#chart-btn-sr');

        ppBtn.addEventListener('click', () => {
            currentChartType = 'pp';
            ppBtn.classList.add('active');
            srBtn.classList.remove('active');
            applyFiltersAndRender(viewElement);
        });
        srBtn.addEventListener('click', () => {
            currentChartType = 'sr';
            srBtn.classList.add('active');
            ppBtn.classList.remove('active');
            applyFiltersAndRender(viewElement);
        });
        
        viewInitialized = true;
    }

    try {
        const [stats, replaysData] = await Promise.all([
            getPlayerStats(playerName), 
            getReplays(playerName, 1, 100000)
        ]);

        statsContainer.innerHTML = `
            <div class="stat-item"><span class="stat-label">Total PP</span><span class="stat-value">${stats.total_pp.toLocaleString()}</span></div>
            <div class="stat-item"><span class="stat-label">Play Count</span><span class="stat-value">${stats.play_count.toLocaleString()}</span></div>
            <div class="stat-item"><span class="stat-label">Top Play</span><span class="stat-value">${stats.top_play_pp.toLocaleString()}pp</span></div>
        `;
        
        const replays = replaysData.replays;
        allScores = replays;
        
        const uniqueMods = [...new Set(replays.flatMap(r => getModsFromInt(r.mods_used)))].sort();
        uniqueMods.forEach(mod => {
            const button = document.createElement('button');
            button.className = 'mod-button';
            button.textContent = mod;
            button.dataset.mod = mod;
            button.addEventListener('click', () => {
                button.classList.toggle('active');
                if (activeModFilters.has(mod)) {
                    activeModFilters.delete(mod);
                } else {
                    activeModFilters.add(mod);
                }
                applyFiltersAndRender(viewElement);
            });
            modContainer.appendChild(button);
        });

        applyFiltersAndRender(viewElement);

    } catch (error) {
        console.error('Error loading profile:', error);
        statusMessage.textContent = error.message;
        viewElement.querySelector('#profile-replays-container').innerHTML = `<p>Error loading profile data.</p>`;
    }
}