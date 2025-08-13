import { getReplays } from '../services/api.js';
import { createReplayCard } from '../components/ReplayCard.js';
import { renderPagination } from '../components/Pagination.js';

let searchTimeout;
let currentSearchTerm = '';

export function createScoresView() {
    const view = document.createElement('div');
    view.id = 'scores-view';
    view.className = 'view';
    view.innerHTML = `
        <h2>All Scores</h2>
        <div class="search-container">
            <input type="search" id="scores-search" class="search-input" placeholder="Search by title, artist, mapper...">
        </div>
        <div id="scores-pagination" class="pagination-controls"></div>
        <div id="replays-container"></div>
    `;

    const searchInput = view.querySelector('#scores-search');
    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            currentSearchTerm = searchInput.value;
            loadScores(view, 1, currentSearchTerm);
        }, 300); // 300ms debounce
    });

    return view;
}

export async function loadScores(viewElement, page = 1, searchTerm = currentSearchTerm) {
    const container = viewElement.querySelector('#replays-container');
    const paginationContainer = viewElement.querySelector('#scores-pagination');
    const statusMessage = document.getElementById('status-message');
    
    currentSearchTerm = searchTerm;
    statusMessage.textContent = 'Loading replay data...';
    container.innerHTML = '';
    paginationContainer.innerHTML = '';

    try {
        const response = await getReplays(null, page, 50, searchTerm);
        const { replays, total } = response;
        
        const start = Math.min((page - 1) * 50 + 1, total);
        const end = Math.min(start + replays.length - 1, total);

        statusMessage.textContent = total > 0 ? `Displaying ${start}-${end} of ${total} scores.` : 'No replays found. Try scanning or adjusting your search.';
        
        replays.forEach(replay => {
            const card = createReplayCard(replay);
            container.appendChild(card);
        });

        if (total > 0) {
            renderPagination(paginationContainer, page, total, 50, (newPage) => {
                loadScores(viewElement, newPage, searchTerm);
            });
        }

    } catch (error) {
        console.error('Error fetching data:', error);
        statusMessage.textContent = error.message;
    }
}