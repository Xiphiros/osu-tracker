import { getPlayers, getConfig } from './services/api.js';
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
                    const activeViewName = document.querySelector('.view[style*="display: block"]')?.dataset.viewName;
                    if (activeViewName === 'profile') {
                        loadProfile(views.profile, currentPlayer);
                    }
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
        stopAudio();
        document.getElementById('status-message').textContent = '';
        navLinks.forEach(link => link.classList.remove('active'));

        for (const key in views) {
            views[key].style.display = 'none';
        }

        const view = views[viewName];
        const link = document.querySelector(`.nav-link[data-view="${viewName}"]`);
        
        if (view) {
            view.style.display = 'block';
            // Dispatch a custom event to notify the view it's being activated.
            // This is useful for views that need to load data upon display, like Config.
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
                const statusMessage = document.getElementById('status-message');
                statusMessage.textContent = 'Please select a player to view their profile.';
                return;
            }

            const activeLink = document.querySelector('.nav-link.active');
            if (activeLink && activeLink.getAttribute('data-view') === viewName) {
                return;
            }

            switchView(viewName);
        });
    });

    mainContent.addEventListener('datachanged', async () => {
        console.log('Data changed event received, refreshing...');
        const config = await getConfig();
        currentPlayer = config.default_player;
        
        await populatePlayerSelector();
        
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
        const config = await getConfig();
        currentPlayer = config.default_player;
        await populatePlayerSelector();
        
        const players = await getPlayers();
        if (currentPlayer) {
            switchView('profile');
        } else if (players.length > 0) {
            switchView('scores');
        } else {
            switchView('config');
        }
    }

    initializeApp();
});