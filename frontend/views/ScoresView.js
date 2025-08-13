import { getReplays } from '../services/api.js';
import { createReplayCard } from '../components/ReplayCard.js';
import { renderPagination } from '../components/Pagination.js';

export function createScoresView() {
    const view = document.createElement('div');
    view.id = 'scores-view';
    view.className = 'view';
    view.innerHTML = `
        <h2>All Scores</h2>
        <div id="scores-pagination" class="pagination-controls"></div>
        <div id="replays-container"></div>
    `;
    return view;
}

export async function loadScores(viewElement, page = 1) {
    const container = viewElement.querySelector('#replays-container');
    const paginationContainer = viewElement.querySelector('#scores-pagination');
    const statusMessage = document.getElementById('status-message');
    
    statusMessage.textContent = 'Loading replay data...';
    container.innerHTML = '';
    paginationContainer.innerHTML = '';

    try {
        const response = await getReplays(null, page);
        const { replays, total } = response;
        
        const start = Math.min((page - 1) * 50 + 1, total);
        const end = Math.min(start + replays.length - 1, total);

        statusMessage.textContent = total > 0 ? `Displaying ${start}-${end} of ${total} scores.` : 'No replays found. Try scanning.';
        
        replays.forEach(replay => {
            const card = createReplayCard(replay);
            container.appendChild(card);
        });

        if (total > 0) {
            renderPagination(paginationContainer, page, total, 50, (newPage) => {
                loadScores(viewElement, newPage);
            });
        }

    } catch (error) {
        console.error('Error fetching data:', error);
        statusMessage.textContent = error.message;
    }
}