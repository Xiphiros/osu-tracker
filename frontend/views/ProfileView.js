import { getReplays, getPlayerStats } from '../services/api.js';
import { createReplayCard } from '../components/ReplayCard.js';

let allScores = [];
let viewInitialized = false;

// --- Helper Functions ---

// Based on the .osr file format spec for the Mods integer
const MODS = {
    NF: 1, EZ: 2, TD: 4, HD: 8, HR: 16, SD: 32, DT: 64, RX: 128, HT: 256, NC: 512, FL: 1024,
};

function getModsFromInt(modInt) {
    const activeMods = [];
    for (const modName in MODS) {
        if (modInt & MODS[modName]) {
            // Special case: NC is DT + NC. Don't show DT if NC is present.
            if (modName === 'DT' && (modInt & MODS.NC)) continue;
            activeMods.push(modName);
        }
    }
    return activeMods;
}

function calculateAccuracy(replay) {
    const totalHits = replay.num_300s + replay.num_100s + replay.num_50s + replay.num_misses;
    if (totalHits === 0) return 0;
    return ((replay.num_300s * 300 + replay.num_100s * 100 + replay.num_50s * 50) / (totalHits * 300)) * 100;
}

// --- Main View and Logic ---

function applyFiltersAndRender(viewElement) {
    const replaysContainer = viewElement.querySelector('#profile-replays-container');
    replaysContainer.innerHTML = '';

    // Get current filter values from the UI
    const sortValue = viewElement.querySelector('#sort-select').value;
    const modFilter = viewElement.querySelector('#mod-filter').value.toUpperCase().trim();
    const minAcc = parseFloat(viewElement.querySelector('#acc-filter').value) || 0;
    const minStars = parseFloat(viewElement.querySelector('#stars-filter').value) || 0;

    let filteredScores = allScores;

    // Apply filters
    if (modFilter) {
        filteredScores = filteredScores.filter(replay => getModsFromInt(replay.mods_used).includes(modFilter));
    }
    if (minAcc > 0) {
        filteredScores = filteredScores.filter(replay => calculateAccuracy(replay) >= minAcc);
    }
    if (minStars > 0) {
        filteredScores = filteredScores.filter(replay => (replay.stars || 0) >= minStars);
    }

    // Apply sorting
    filteredScores.sort((a, b) => {
        switch (sortValue) {
            case 'pp': return (b.pp || 0) - (a.pp || 0);
            case 'score': return b.total_score - a.total_score;
            case 'date': return new Date(b.played_at) - new Date(a.played_at);
            case 'stars': return (b.stars || 0) - (a.stars || 0);
            default: return (b.pp || 0) - (a.pp || 0);
        }
    });
    
    // Render the cards
    if (filteredScores.length > 0) {
        filteredScores.forEach(replay => {
            const card = createReplayCard(replay);
            replaysContainer.appendChild(card);
        });
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
            <div class="profile-filters">
                <select id="sort-select">
                    <option value="pp">Sort by: Highest PP</option>
                    <option value="score">Sort by: Highest Score</option>
                    <option value="date">Sort by: Most Recent</option>
                    <option value="stars">Sort by: Highest Stars</option>
                </select>
                <input type="text" id="mod-filter" placeholder="Filter by mod (e.g. HD)">
                <input type="number" id="acc-filter" min="0" max="100" step="0.1" placeholder="Min Accuracy %">
                <input type="number" id="stars-filter" min="0" step="0.1" placeholder="Min Stars ★">
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

    nameHeader.textContent = `${playerName}'s Profile`;
    statsContainer.innerHTML = 'Loading stats...';
    statusMessage.textContent = `Loading ${playerName}'s profile...`;
    
    // Set up event listeners only once
    if (!viewInitialized) {
        viewElement.querySelectorAll('.profile-filters > *').forEach(el => {
            el.addEventListener('input', () => applyFiltersAndRender(viewElement));
        });
        viewInitialized = true;
    }

    try {
        const [stats, replays] = await Promise.all([
            getPlayerStats(playerName),
            getReplays(playerName)
        ]);

        statsContainer.innerHTML = `
            <div class="stat-item"><span class="stat-label">Total PP</span><span class="stat-value">${stats.total_pp.toLocaleString()}</span></div>
            <div class="stat-item"><span class="stat-label">Play Count</span><span class="stat-value">${stats.play_count.toLocaleString()}</span></div>
            <div class="stat-item"><span class="stat-label">Top Play</span><span class="stat-value">${stats.top_play_pp.toLocaleString()}pp</span></div>
        `;

        allScores = replays;
        applyFiltersAndRender(viewElement);

    } catch (error) {
        console.error('Error loading profile:', error);
        statusMessage.textContent = error.message;
        viewElement.querySelector('#profile-replays-container').innerHTML = `<p>Error loading profile data.</p>`;
    }
}