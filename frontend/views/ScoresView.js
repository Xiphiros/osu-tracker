import { getReplays } from '../services/api.js';
import { createReplayCard } from '../components/ReplayCard.js';

export function createScoresView() {
    const view = document.createElement('div');
    view.id = 'scores-view';
    view.className = 'view';

    const header = document.createElement('h2');
    header.textContent = 'All Scores';
    
    const container = document.createElement('div');
    container.id = 'replays-container';
    
    view.append(header, container);
    
    return view;
}

export async function loadScores(viewElement) {
    const container = viewElement.querySelector('#replays-container');
    const statusMessage = document.getElementById('status-message'); // Assume global status message
    
    statusMessage.textContent = 'Loading replay data...';
    container.innerHTML = '';

    try {
        const replays = await getReplays();
        statusMessage.textContent = replays.length > 0 ? `Displaying ${replays.length} scores.` : 'No replays found. Try scanning.';
        
        replays.forEach(replay => {
            const card = createReplayCard(replay);
            container.appendChild(card);
        });

    } catch (error) {
        console.error('Error fetching data:', error);
        statusMessage.textContent = error.message;
    }
}