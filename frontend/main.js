import { getReplays, scanReplays, getPlayers } from './services/api.js';
import { createScoresView, loadScores } from './views/ScoresView.js';
import { createProfileView, loadProfile } from './views/ProfileView.js';
import { createBeatmapsView, loadBeatmaps } from './views/BeatmapsView.js';
import { createConfigView } from './views/ConfigView.js';
import { createRecommenderView } from './views/RecommenderView.js';
import { stopAudio } from './utils/audioPlayer.js';

document.addEventListener('DOMContentLoaded', () => {
    const mainContent = document.getElementById('main-content');
    const navLinks = document.querySelectorAll('.nav-link');
    const userSelectorContainer = document.getElementById('user-selector-container');

    let currentPlayer = null; // State to track the selected player

    const views = {
        scores: createScoresView(),
        profile: createProfileView(),
        beatmaps: createBeatmapsView(),
        recommender: createRecommenderView(),
        config: createConfigView(),
    };
    
    // Add all views to the DOM, but keep them hidden initially
    for (const key in views) {
        views[key].dataset.viewName = key;
        views[key].style.display = 'none'; // Explicitly hide all views
        mainContent.appendChild(views[key]);
    }

    async function populatePlayerSelector() {
        try {
            const players = await getPlayers();
            if (players.length > 0) {
                const selector = document.createElement('select');
                selector.id = 'player-selector';
                selector.innerHTML = `<option value="">-- Select a Player --</option>`;
                players.forEach(player => {
                    const isSelected = player === currentPlayer;
                    selector.innerHTML += `<option value="${player}" ${isSelected ? 'selected' : ''}>${player}</option>`;
                });
                userSelectorContainer.innerHTML = '';
                userSelectorContainer.appendChild(selector);
                
                selector.addEventListener('change', (e) => {
                    currentPlayer = e.target.value;
                    // If a player is selected, switch to their profile. Otherwise, go to scores.
                    switchView(currentPlayer ? 'profile' : 'scores');
                });
            } else {
                userSelectorContainer.innerHTML = '<p style="font-size: 0.8em; color: #aaa; text-align: center;">No players found. Please run a scan from the Config page.</p>';
            }
        } catch (error) {
            console.error("Failed to load players:", error);
            userSelectorContainer.innerHTML = '<p style="font-size: 0.8em; color: #999;">Could not load players.</p>';
        }
    }

    function switchView(viewName) {
        stopAudio(); // Stop any playing music when changing views
        document.getElementById('status-message').textContent = ''; // Clear status message on view switch
        navLinks.forEach(link => link.classList.remove('active'));

        // Hide all views
        for (const key in views) {
            views[key].style.display = 'none';
        }

        const view = views[viewName];
        const link = document.querySelector(`.nav-link[data-view="${viewName}"]`);
        
        if (view) {
            view.style.display = 'block'; // Show only the target view
            // Load data for the activated view
            if (viewName === 'scores') loadScores(view);
            else if (viewName === 'profile') loadProfile(view, currentPlayer);
            else if (viewName === 'beatmaps') loadBeatmaps(view);
            // Config and Recommender views require no initial data loading
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
                // Display a message in the global status footer and do not switch views.
                const statusMessage = document.getElementById('status-message');
                statusMessage.textContent = 'Please select a player to view their profile.';
                return;
            }

            const activeLink = document.querySelector('.nav-link.active');
            if (activeLink && activeLink.getAttribute('data-view') === viewName) {
                return; // Do nothing if clicking the already active view
            }

            switchView(viewName);
        });
    });

    // Listen for the custom 'datachanged' event from the Config view
    mainContent.addEventListener('datachanged', () => {
        console.log('Data changed event received, refreshing player list and current view.');
        populatePlayerSelector();
        
        // Also refresh the current view
        const activeView = mainContent.querySelector('.view.active');
        if (activeView) {
            const viewName = activeView.dataset.viewName;
            const view = views[viewName];
            if (view) {
                switch(viewName) {
                    case 'scores':
                        loadScores(view);
                        break;
                    case 'profile':
                        if (currentPlayer) loadProfile(view, currentPlayer);
                        break;
                    case 'beatmaps':
                        loadBeatmaps(view);
                        break;
                }
            }
        }
    });

    async function initializeApp() {
        await populatePlayerSelector();
        // Start on the main scores view if players exist, otherwise on config page
        const players = await getPlayers();
        switchView(players.length > 0 ? 'scores' : 'config');
    }

    initializeApp();
});