import { scanReplays } from './services/api.js';
import { createScoresView, loadScores } from './views/ScoresView.js';

document.addEventListener('DOMContentLoaded', () => {
    const mainContent = document.getElementById('main-content');
    const scanButton = document.getElementById('scan-button');
    const statusMessage = document.getElementById('status-message');
    const navLinks = document.querySelectorAll('.nav-link');

    const views = {
        scores: createScoresView(),
        // Stubs for other views
        beatmaps: createStubView('Beatmaps'),
        profile: createStubView('Profile')
    };
    
    // Add all views to the DOM, but keep them hidden
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

    function switchView(viewName) {
        // Hide all views
        document.querySelectorAll('#main-content .view').forEach(v => v.classList.remove('active'));
        // Deactivate all nav links
        navLinks.forEach(link => link.classList.remove('active'));

        // Show the selected view and activate the link
        const view = views[viewName];
        const link = document.querySelector(`.nav-link[data-view="${viewName}"]`);
        
        if (view) {
            view.classList.add('active');
            if (viewName === 'scores') {
                loadScores(view);
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
            switchView(viewName);
        });
    });

    scanButton.addEventListener('click', async () => {
        statusMessage.textContent = 'Scanning...';
        scanButton.disabled = true;
        try {
            const result = await scanReplays();
            statusMessage.textContent = result.status || 'Scan complete.';
            // If we are on the scores view, refresh it
            if (views.scores.classList.contains('active')) {
                loadScores(views.scores);
            }
        } catch (error) {
            console.error('Error during scan:', error);
            statusMessage.textContent = 'Error during scan.';
        } finally {
            scanButton.disabled = false;
        }
    });

    // Initialize the app by showing the default view
    switchView('scores');
});