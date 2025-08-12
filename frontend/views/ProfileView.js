import { getReplays, getPlayerStats } from '../services/api.js';
import { createReplayCard } from '../components/ReplayCard.js';

export function createProfileView() {
    const view = document.createElement('div');
    view.id = 'profile-view';
    view.className = 'view';
    view.innerHTML = `
        <div id="profile-header">
            <h2 id="profile-player-name"></h2>
            <div id="profile-stats" class="stats-container"></div>
        </div>
        <div id="profile-replays-container"></div>
    `;
    return view;
}

export async function loadProfile(viewElement, playerName) {
    if (!playerName) {
        viewElement.innerHTML = '<h2>Select a player to view their profile.</h2>';
        return;
    }

    const nameHeader = viewElement.querySelector('#profile-player-name');
    const statsContainer = viewElement.querySelector('#profile-stats');
    const replaysContainer = viewElement.querySelector('#profile-replays-container');
    const statusMessage = document.getElementById('status-message');

    nameHeader.textContent = `${playerName}'s Profile`;
    statsContainer.innerHTML = 'Loading stats...';
    replaysContainer.innerHTML = '';
    statusMessage.textContent = `Loading ${playerName}'s profile...`;

    try {
        // Fetch stats and replays in parallel for faster loading
        const [stats, replays] = await Promise.all([
            getPlayerStats(playerName),
            getReplays(playerName)
        ]);

        // Display stats
        statsContainer.innerHTML = `
            <div class="stat-item">
                <span class="stat-label">Total PP</span>
                <span class="stat-value">${stats.total_pp.toLocaleString()}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Play Count</span>
                <span class="stat-value">${stats.play_count.toLocaleString()}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Top Play</span>
                <span class="stat-value">${stats.top_play_pp.toLocaleString()}pp</span>
            </div>
        `;

        // Sort replays by PP (descending) for display
        replays.sort((a, b) => (b.pp || 0) - (a.pp || 0));

        // Display replays
        if (replays.length > 0) {
            replays.forEach(replay => {
                const card = createReplayCard(replay);
                replaysContainer.appendChild(card);
            });
            statusMessage.textContent = `Displaying ${replays.length} scores for ${playerName}.`;
        } else {
            replaysContainer.innerHTML = '<p>No scores found for this player.</p>';
            statusMessage.textContent = `No scores found for ${playerName}.`;
        }

    } catch (error) {
        console.error('Error loading profile:', error);
        statusMessage.textContent = error.message;
        replaysContainer.innerHTML = `<p>Error loading profile data.</p>`;
    }
}