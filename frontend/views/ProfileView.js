import { getReplays, getPlayerStats } from '../services/api.js';
import { createReplayCard } from '../components/ReplayCard.js';
import { getModsFromInt } from '../utils/mods.js';

let allScores = [];
let viewInitialized = false;
let profileChart = null;
const activeModFilters = new Set();

function calculateAccuracy(replay) {
    const totalHits = replay.num_300s + replay.num_100s + replay.num_50s + replay.num_misses;
    if (totalHits === 0) return 0;
    return ((replay.num_300s * 300 + replay.num_100s * 100 + replay.num_50s * 50) / (totalHits * 300)) * 100;
}

function groupScoresByDay(scores) {
    const grouped = {};
    scores.forEach(score => {
        if (!score.played_at) return;
        const date = new Date(score.played_at).toISOString().split('T')[0];
        if (!grouped[date]) {
            grouped[date] = [];
        }
        grouped[date].push(score);
    });
    return grouped;
}

/**
 * Renders or updates the profile chart.
 * @param {object | null} chartJsConfig - The complete Chart.js configuration object, or null to hide the chart.
 */
function renderProfileChart(chartJsConfig) {
    const chartWrapper = document.getElementById('chart-wrapper');
    if (!chartWrapper) return;
    
    if (profileChart) {
        profileChart.destroy();
        profileChart = null;
    }
    
    if (!chartJsConfig || (chartJsConfig.data.datasets[0] && chartJsConfig.data.datasets[0].data.length === 0)) {
        chartWrapper.style.display = 'none';
        return;
    }
    chartWrapper.style.display = 'block';

    const ctx = document.getElementById('profile-chart').getContext('2d');
    profileChart = new Chart(ctx, chartJsConfig);
}

function applyFiltersAndRender(viewElement) {
    const replaysContainer = viewElement.querySelector('#profile-replays-container');
    const analyticsContainer = viewElement.querySelector('#profile-analytics');
    replaysContainer.innerHTML = '';
    analyticsContainer.innerHTML = '';

    const sortValue = viewElement.querySelector('#sort-select').value;
    const chartType = viewElement.querySelector('#chart-type-select').value;
    const minAcc = parseFloat(viewElement.querySelector('#acc-filter-min').value) || 0;
    const maxAcc = parseFloat(viewElement.querySelector('#acc-filter-max').value) || 100;
    const minStars = parseFloat(viewElement.querySelector('#stars-filter-min').value) || 0;
    const minBpm = parseFloat(viewElement.querySelector('#bpm-filter-min').value) || 0;
    const maxBpm = parseFloat(viewElement.querySelector('#bpm-filter-max').value) || Infinity;
    const exactMatch = viewElement.querySelector('#exact-mod-match-toggle').checked;

    let filteredScores = allScores.filter(s => s.played_at);

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
        return acc >= minAcc && acc <= maxAcc && stars >= minStars && bpm >= minBpm && bpm <= maxBpm;
    });

    if (filteredScores.length > 0) {
        const scoresForAnalytics = [...filteredScores].sort((a, b) => (b.stars || 0) - (a.stars || 0)).slice(0, 100);
        const totalStars = scoresForAnalytics.reduce((sum, score) => sum + (score.stars || 0), 0);
        const avgStars = scoresForAnalytics.length > 0 ? (totalStars / scoresForAnalytics.length).toFixed(2) : '0.00';
        analyticsContainer.innerHTML = `<div class="stat-item"><span class="stat-label">Average Star Rating (Top ${scoresForAnalytics.length} Filtered Plays)</span><span class="stat-value">★ ${avgStars}</span></div>`;
    }

    const scoresForChart = [...filteredScores].sort((a, b) => new Date(a.played_at) - new Date(b.played_at));
    let chartJsConfig = null;

    const baseChartOptions = (yLabel) => ({
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: { type: 'time', time: { unit: 'month', tooltipFormat: 'MMM d, yyyy', displayFormats: { month: 'MMM yyyy' } }, grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#ccc' } },
            y: { beginAtZero: false, title: { display: true, text: yLabel, color: '#ccc' }, grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#ccc' } }
        },
        plugins: {
            legend: { display: false },
            tooltip: { callbacks: { title: context => new Date(context[0].parsed.x).toLocaleDateString(), label: context => `${yLabel}: ${context.parsed.y.toFixed(2)}` } }
        }
    });

    switch (chartType) {
        case 'pp_progression': {
            let cumulativePlays = [];
            const data = scoresForChart.map(score => {
                cumulativePlays.push(score);
                const ppPlays = cumulativePlays.filter(p => p.pp > 0).sort((a, b) => b.pp - a.pp);
                const totalPp = ppPlays.reduce((sum, p, i) => sum + p.pp * (0.95 ** i), 0);
                return { x: new Date(score.played_at), y: totalPp };
            });
            chartJsConfig = {
                type: 'line',
                data: { datasets: [{ label: 'Total PP (Filtered)', data, backgroundColor: 'rgba(0, 170, 255, 0.8)', borderColor: 'rgba(0, 170, 255, 0.5)', borderWidth: 2, pointRadius: 2, tension: 0.1 }] },
                options: baseChartOptions('Total PP (Filtered)')
            };
            break;
        }
        case 'top_play_pp': {
            let maxPp = 0;
            const data = [];
            scoresForChart.forEach(score => {
                if ((score.pp || 0) > maxPp) {
                    maxPp = score.pp;
                    data.push({ x: new Date(score.played_at), y: maxPp });
                }
            });
            chartJsConfig = {
                type: 'line',
                data: { datasets: [{ label: 'Top Play (PP)', data, stepped: true, backgroundColor: 'rgba(0, 170, 255, 0.8)', borderColor: 'rgba(0, 170, 255, 0.5)', borderWidth: 2, pointRadius: 3 }] },
                options: baseChartOptions('Top Play (PP)')
            };
            break;
        }
        case 'daily_avg_pp': {
            const grouped = groupScoresByDay(scoresForChart);
            const data = Object.keys(grouped).sort().map(date => { const dayScores = grouped[date]; const total = dayScores.reduce((sum, s) => sum + (s.pp || 0), 0); return { x: date, y: total / dayScores.length }; });
            chartJsConfig = {
                type: 'line',
                data: { datasets: [{ label: 'Daily Avg PP', data, backgroundColor: 'rgba(0, 170, 255, 0.8)', borderColor: 'rgba(0, 170, 255, 0.5)', tension: 0.2, pointRadius: 2 }] },
                options: baseChartOptions('Daily Avg PP')
            };
            break;
        }
        case 'highest_sr': {
            let maxSr = 0;
            const data = [];
             scoresForChart.forEach(score => {
                if ((score.stars || 0) > maxSr) {
                    maxSr = score.stars;
                    data.push({ x: new Date(score.played_at), y: maxSr });
                }
            });
            chartJsConfig = {
                type: 'line',
                data: { datasets: [{ label: 'Highest SR Passed', data, stepped: true, backgroundColor: 'rgba(0, 170, 255, 0.8)', borderColor: 'rgba(0, 170, 255, 0.5)', borderWidth: 2, pointRadius: 3 }] },
                options: baseChartOptions('Highest SR Passed')
            };
            break;
        }
        case 'daily_avg_sr': {
            const grouped = groupScoresByDay(scoresForChart);
            const data = Object.keys(grouped).sort().map(date => { const dayScores = grouped[date]; const total = dayScores.reduce((sum, s) => sum + (s.stars || 0), 0); return { x: date, y: total / dayScores.length }; });
            chartJsConfig = {
                type: 'line',
                data: { datasets: [{ label: 'Daily Avg SR', data, backgroundColor: 'rgba(0, 170, 255, 0.8)', borderColor: 'rgba(0, 170, 255, 0.5)', tension: 0.2, pointRadius: 2 }] },
                options: baseChartOptions('Daily Avg SR')
            };
            break;
        }
        case 'daily_avg_acc': {
            const grouped = groupScoresByDay(scoresForChart);
            const data = Object.keys(grouped).sort().map(date => { const dayScores = grouped[date]; const total = dayScores.reduce((sum, s) => sum + calculateAccuracy(s), 0); return { x: date, y: total / dayScores.length }; });
            chartJsConfig = {
                type: 'line',
                data: { datasets: [{ label: 'Daily Avg Accuracy (%)', data, backgroundColor: 'rgba(0, 170, 255, 0.8)', borderColor: 'rgba(0, 170, 255, 0.5)', tension: 0.2, pointRadius: 2 }] },
                options: baseChartOptions('Daily Avg Accuracy (%)')
            };
            break;
        }
        case 'play_count': {
            const grouped = groupScoresByDay(scoresForChart);
            const data = Object.keys(grouped).sort().map(date => ({ x: date, y: grouped[date].length }));
            chartJsConfig = {
                type: 'line',
                data: { datasets: [{ label: 'Daily Play Count', data, backgroundColor: 'rgba(0, 170, 255, 0.8)', borderColor: 'rgba(0, 170, 255, 0.5)', tension: 0.2, pointRadius: 2 }] },
                options: baseChartOptions('Daily Play Count')
            };
            break;
        }
        case 'cumulative_plays': {
            const data = scoresForChart.map((score, index) => ({ x: new Date(score.played_at), y: index + 1 }));
            chartJsConfig = {
                type: 'line',
                data: { datasets: [{ label: 'Cumulative Play Count', data, backgroundColor: 'rgba(0, 170, 255, 0.8)', borderColor: 'rgba(0, 170, 255, 0.5)', borderWidth: 2, pointRadius: 0, tension: 0.1 }] },
                options: baseChartOptions('Cumulative Play Count')
            };
            break;
        }
        case 'pp_vs_acc': {
            const data = filteredScores.filter(s => s.pp).map(s => ({ x: calculateAccuracy(s), y: s.pp }));
            chartJsConfig = {
                type: 'scatter',
                data: { datasets: [{ label: 'PP vs Accuracy', data, backgroundColor: 'rgba(0, 170, 255, 0.7)' }] },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    scales: {
                        x: { type: 'linear', position: 'bottom', title: { display: true, text: 'Accuracy (%)', color: '#ccc' }, grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#ccc' } },
                        y: { title: { display: true, text: 'PP', color: '#ccc' }, grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#ccc' } }
                    },
                    plugins: { legend: { display: false }, tooltip: { callbacks: { label: context => `PP: ${context.parsed.y.toFixed(2)}, Acc: ${context.parsed.x.toFixed(2)}%` } } }
                }
            };
            break;
        }
        case 'sr_distribution': {
            const starCounts = {};
            filteredScores.forEach(s => { if (!s.stars) return; const bucket = (Math.floor(s.stars * 2) / 2).toFixed(1); starCounts[bucket] = (starCounts[bucket] || 0) + 1; });
            const sortedBuckets = Object.keys(starCounts).sort((a,b) => parseFloat(a) - parseFloat(b));
            const labels = sortedBuckets.map(b => `${b} - ${(parseFloat(b) + 0.49).toFixed(1)} ★`);
            const data = sortedBuckets.map(b => starCounts[b]);
            chartJsConfig = {
                type: 'line',
                data: { 
                    labels, 
                    datasets: [{ 
                        label: 'Play Count', 
                        data, 
                        backgroundColor: 'rgba(0, 170, 255, 0.5)',
                        borderColor: 'rgba(0, 170, 255, 0.8)',
                        fill: true,
                        tension: 0.2
                    }] 
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    scales: {
                        x: { title: { display: true, text: 'Star Rating', color: '#ccc' }, grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#ccc' } },
                        y: { title: { display: true, text: 'Play Count', color: '#ccc' }, grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#ccc' }, beginAtZero: true }
                    },
                    plugins: { legend: { display: false } }
                }
            };
            break;
        }
    }
    renderProfileChart(chartJsConfig);
    
    filteredScores.sort((a, b) => {
        switch (sortValue) {
            case 'pp': return (b.pp || 0) - (a.pp || 0);
            case 'score': return b.total_score - a.total_score;
            case 'date': return new Date(b.played_at) - new Date(a.played_at);
            case 'stars': return (b.stars || 0) - (a.stars || 0);
            default: return (b.pp || 0) - (a.pp || 0);
        }
    });
    
    replaysContainer.innerHTML = filteredScores.length > 0 ? '' : '<p>No scores match the current filters.</p>';
    filteredScores.forEach(replay => replaysContainer.appendChild(createReplayCard(replay)));
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
                <select id="chart-type-select">
                    <optgroup label="Progression Over Time">
                        <option value="pp_progression">PP Progression (Filtered)</option>
                        <option value="top_play_pp">Top Play PP</option>
                        <option value="highest_sr">Highest SR Passed</option>
                        <option value="cumulative_plays">Cumulative Play Count</option>
                    </optgroup>
                    <optgroup label="Daily Averages &amp; Activity">
                        <option value="daily_avg_pp">Daily Average PP</option>
                        <option value="daily_avg_sr">Daily Average SR</option>
                        <option value="daily_avg_acc">Daily Average Accuracy</option>
                        <option value="play_count">Daily Play Count</option>
                    </optgroup>
                    <optgroup label="Score Distributions">
                        <option value="pp_vs_acc">PP vs. Accuracy Scatter</option>
                        <option value="sr_distribution">Play Count by Star Rating</option>
                    </optgroup>
                </select>
            </div>
            <div id="chart-wrapper" class="chart-wrapper" style="display: none;">
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
        const allFilters = '#sort-select, #acc-filter-min, #acc-filter-max, #stars-filter-min, #bpm-filter-min, #bpm-filter-max, #exact-mod-match-toggle, #chart-type-select';
        viewElement.querySelectorAll(allFilters).forEach(el => {
            el.addEventListener('input', () => applyFiltersAndRender(viewElement));
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
        
        allScores = replaysData.replays;
        
        const uniqueMods = [...new Set(allScores.flatMap(r => getModsFromInt(r.mods_used)))].sort();
        uniqueMods.forEach(mod => {
            const button = document.createElement('button');
            button.className = 'mod-button';
            button.textContent = mod;
            button.dataset.mod = mod;
            button.addEventListener('click', () => {
                button.classList.toggle('active');
                if (activeModFilters.has(mod)) activeModFilters.delete(mod);
                else activeModFilters.add(mod);
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