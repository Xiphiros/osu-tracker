import { getReplays, scanReplays, getPlayers } from './services/api.js';
import { createScoresView, loadScores } from './views/ScoresView.js';
import { createProfileView, loadProfile } from './views/ProfileView.js';
import { createBeatmapsView, loadBeatmaps } from './views/BeatmapsView.js';

document.addEventListener('DOMContentLoaded', () => {
    const mainContent = document.getElementById('main-content');
    const scanButton = document.getElementById('scan-button');
    const statusMessage = document.getElementById('status-message');
    const navLinks = document.querySelectorAll('.nav-link');
    const userSelectorContainer = document.getElementById('user-selector-container');

    let currentPlayer = null; // State to track the selected player

    const views = {
        scores: createScoresView(),
        profile: createProfileView(),
        beatmaps: createBeatmapsView(),
    };
    
    // Add all views to the DOM, but keep them hidden initially
    for (const key in views) {
        views[key].dataset.viewName = key;
        mainContent.appendChild(views[key]);
    }

    function createStubView(title) {
        const view = document.createElement('div');
        view.className = 'view';
        view.innerHTML = `<h2>${title}</h2><p>This section is under construction.</p>`;
        return view;
    }

    async function populatePlayerSelector() {
        try {
            const players = await getPlayers();
            if (players.length > 0) {
                const selector = document.createElement('select');
                selector.id = 'player-selector';
                selector.innerHTML = `<option value="">-- Select a Player --</option>`;
                players.forEach(player => {
                    selector.innerHTML += `<option value="${player}">${player}</option>`;
                });
                userSelectorContainer.innerHTML = '';
                userSelectorContainer.appendChild(selector);
                
                selector.addEventListener('change', (e) => {
                    currentPlayer = e.target.value;
                    if (currentPlayer) {
                        switchView('profile'); // Switch to profile view when a player is selected
                    } else {
                        switchView('scores'); // Go back to all scores if "Select" is chosen
                    }
                });
            } else {
                userSelectorContainer.innerHTML = '<p style="font-size: 0.8em; color: #aaa; text-align: center;">No players found. Scan for replays.</p>';
            }
        } catch (error) {
            console.error("Failed to load players:", error);
            userSelectorContainer.innerHTML = '<p style="font-size: 0.8em; color: #999;">Could not load players.</p>';
        }
    }

    function switchView(viewName) {
        document.querySelectorAll('#main-content .view').forEach(v => v.classList.remove('active'));
        navLinks.forEach(link => link.classList.remove('active'));

        const view = views[viewName];
        const link = document.querySelector(`.nav-link[data-view="${viewName}"]`);
        
        if (view) {
            view.classList.add('active');
            if (viewName === 'scores') {
                loadScores(view);
            } else if (viewName === 'profile') {
                loadProfile(view, currentPlayer);
            } else if (viewName === 'beatmaps') {
                loadBeatmaps(view);
            }
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
                statusMessage.textContent = 'Please select a player from the dropdown first.';
                return;
            }
            switchView(viewName);
        });
    });

    scanButton.addEventListener('click', async () => {
        statusMessage.textContent = 'Scanning...';
        scanButton.disabled = true;
        try {
            const result = await scanReplays();
            statusMessage.textContent = result.status || 'Scan complete.';
            
            await populatePlayerSelector();
            
            const activeView = document.querySelector('#main-content .view.active');
            if (activeView) {
                const viewName = activeView.dataset.viewName;
                if (viewName === 'scores') {
                    loadScores(views.scores);
                } else if (viewName === 'profile' && currentPlayer) {
                    loadProfile(views.profile, currentPlayer);
                } else if (viewName === 'beatmaps') {
                    loadBeatmaps(views.beatmaps);
                }
            }

        } catch (error) {
            console.error('Error during scan:', error);
            statusMessage.textContent = 'Error during scan.';
        } finally {
            scanButton.disabled = false;
        }
    });

    async function initializeApp() {
        await populatePlayerSelector();
        switchView('scores'); // Start on the main scores view
    }

    initializeApp();
});