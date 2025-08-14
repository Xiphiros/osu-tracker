import { getPlayers, getConfig, getProgressStatus } from './services/api.js';
import { createScoresView, loadScores } from './views/ScoresView.js';
import { createProfileView, loadProfile } from './views/ProfileView.js';
import { createBeatmapsView, loadBeatmaps } from './views/BeatmapsView.js';
import { createConfigView } from './views/ConfigView.js';
import { createRecommenderView } from './views/RecommenderView.js';
import { stopAudio } from './utils/audioPlayer.js';

let progressInterval = null;
let lastProgress = {};

function updateGlobalStatus(progress) {
    const statusMessage = document.getElementById('status-message');
    const { sync, scan } = progress;
    let message = '';
    
    if (sync.status === 'running') {
        message = sync.message;
    } else if (scan.status === 'running') {
        message = scan.message;
    } else {
        // Show the message of the most recently completed task
        const syncJustCompleted = lastProgress.sync?.status === 'running' && sync.status !== 'running';
        const scanJustCompleted = lastProgress.scan?.status === 'running' && scan.status !== 'running';

        if (syncJustCompleted) {
            message = sync.message;
        } else if (scanJustCompleted) {
            message = scan.message;
        }
    }

    if (statusMessage.textContent !== message) {
        statusMessage.textContent = message;
    }
}

function stopGlobalProgressPolling() {
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
}

async function pollProgress() {
    try {
        const progress = await getProgressStatus();
        
        document.dispatchEvent(new CustomEvent('progressupdated', { detail: progress }));
        updateGlobalStatus(progress);
        
        const syncProgress = progress.sync;
        const lastSyncProgress = lastProgress.sync || {};
        const scanProgress = progress.scan;
        const lastScanProgress = lastProgress.scan || {};

        let shouldRefresh = false;

        // Check for sync updates: either the task just finished, or a batch was completed.
        if (
            (lastSyncProgress.status === 'running' && syncProgress.status !== 'running') ||
            (syncProgress.status === 'running' && syncProgress.batches_done > (lastSyncProgress.batches_done || 0))
        ) {
            shouldRefresh = true;
        }

        // Check for scan updates (final only)
        if (lastScanProgress.status === 'running' && scanProgress.status !== 'running') {
            shouldRefresh = true;
        }

        if (shouldRefresh) {
            document.dispatchEvent(new CustomEvent('datachanged', { bubbles: true }));
        }

        lastProgress = progress;

        if (progress.sync.status !== 'running' && progress.scan.status !== 'running') {
            stopGlobalProgressPolling();
            // Clear the message after a few seconds
            setTimeout(() => {
                const currentStatus = lastProgress.sync.status !== 'running' && lastProgress.scan.status !== 'running';
                if(currentStatus) {
                   document.getElementById('status-message').textContent = '';
                }
            }, 5000);
        }
    } catch (error) {
        console.error("Progress polling failed:", error);
        document.getElementById('status-message').textContent = 'Error fetching status.';
        stopGlobalProgressPolling();
    }
}

function startGlobalProgressPolling() {
    if (progressInterval) return;
    lastProgress = {}; // Reset last progress state
    pollProgress(); // Poll immediately
    progressInterval = setInterval(pollProgress, 1000);
}


document.addEventListener('DOMContentLoaded', () => {
    const mainContent = document.getElementById('main-content');
    const navLinks = document.querySelectorAll('.nav-link');
    const userSelectorContainer = document.getElementById('user-selector-container');

    let currentPlayer = null;

    const views = {
        scores: createScoresView(),
        profile: createProfileView(),
        beatmaps: createBeatmapsView(),
        recommender: createRecommenderView(),
        config: createConfigView(),
    };
    
    for (const key in views) {
        views[key].dataset.viewName = key;
        views[key].style.display = 'none';
        mainContent.appendChild(views[key]);
    }
    
    mainContent.addEventListener('taskstarted', startGlobalProgressPolling);

    function populatePlayerSelector(players, selectedPlayer) {
        try {
            if (players.length > 0) {
                const selector = document.createElement('select');
                selector.id = 'player-selector';
                selector.innerHTML = `<option value="">-- Select a Player --</option>`;
                players.forEach(player => {
                    const isSelected = player === selectedPlayer;
                    selector.innerHTML += `<option value="${player}" ${isSelected ? 'selected' : ''}>${player}</option>`;
                });
                userSelectorContainer.innerHTML = '';
                userSelectorContainer.appendChild(selector);
                
                selector.addEventListener('change', (e) => {
                    currentPlayer = e.target.value;
                    const activeViewName = document.querySelector('.view[style*="display: block"]')?.dataset.viewName;
                    if (activeViewName === 'profile') {
                        loadProfile(views.profile, currentPlayer);
                    }
                });
            } else {
                userSelectorContainer.innerHTML = '<p style="font-size: 0.8em; color: #aaa; text-align: center;">No players found. Please run a scan from the Config page.</p>';
            }
        } catch (error) {
            console.error("Failed to populate player selector:", error);
            userSelectorContainer.innerHTML = '<p style="font-size: 0.8em; color: #999;">Could not load players.</p>';
        }
    }

    function switchView(viewName) {
        stopAudio();
        navLinks.forEach(link => link.classList.remove('active'));

        for (const key in views) {
            const currentView = views[key];
            if (currentView.style.display === 'block') {
                 currentView.dispatchEvent(new CustomEvent('viewdeactivated'));
            }
            currentView.style.display = 'none';
        }

        const view = views[viewName];
        const link = document.querySelector(`.nav-link[data-view="${viewName}"]`);
        
        if (view) {
            view.style.display = 'block';
            view.dispatchEvent(new CustomEvent('viewactivated'));

            if (viewName === 'scores') loadScores(view);
            else if (viewName === 'profile') loadProfile(view, currentPlayer);
            else if (viewName === 'beatmaps') loadBeatmaps(view);
        }
        if (link) {
            link.classList.add('active');
        }
    }

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const viewName = e.target.getAttribute('data-view');
            
            if (viewName === 'profile' && !currentPlayer) {
                document.getElementById('status-message').textContent = 'Please select a player to view their profile.';
                return;
            }

            const activeLink = document.querySelector('.nav-link.active');
            if (activeLink && activeLink.getAttribute('data-view') === viewName) {
                return;
            }

            switchView(viewName);
        });
    });

    document.addEventListener('datachanged', async () => {
        console.log('Data changed event received, refreshing...');

        const players = await getPlayers();

        // Update current player state based on new player list
        if (players.length > 0) {
            const config = await getConfig();
            const defaultPlayer = config.default_player;
            // If current player is invalid or not set, pick a new one.
            if (!currentPlayer || !players.includes(currentPlayer)) {
                currentPlayer = (defaultPlayer && players.includes(defaultPlayer)) ? defaultPlayer : players[0];
            }
        } else {
            currentPlayer = null; // No players, so no current player.
        }
        
        // Now that the state is correct, populate the main UI selector.
        populatePlayerSelector(players, currentPlayer);
        
        // Refresh the current view to reflect any new data
        const activeView = mainContent.querySelector('.view[style*="display: block"]');
        if (activeView) {
            const viewName = activeView.dataset.viewName;
            const view = views[viewName];
            if (view) {
                switch(viewName) {
                    case 'scores': loadScores(view); break;
                    case 'profile': loadProfile(view, currentPlayer); break;
                    case 'beatmaps': loadBeatmaps(view); break;
                    case 'config': view.dispatchEvent(new CustomEvent('viewactivated')); break;
                }
            }
        }
    });

    async function initializeApp() {
        // Check for running tasks on startup
        const initialProgress = await getProgressStatus();
        if(initialProgress.sync.status === 'running' || initialProgress.scan.status === 'running') {
            startGlobalProgressPolling();
        }

        const players = await getPlayers();
        const config = await getConfig();
        
        populatePlayerSelector(players, config.default_player);

        if (players.length > 0) {
            const defaultPlayer = config.default_player;
            currentPlayer = (defaultPlayer && players.includes(defaultPlayer)) ? defaultPlayer : players[0];
            
            // Ensure the selector reflects the actual current player
            const selector = document.getElementById('player-selector');
            if (selector) selector.value = currentPlayer;

            switchView('profile');
        } else {
            // If no players in DB, always go to config page
            currentPlayer = null;
            switchView('config');
        }
    }

    initializeApp();
});