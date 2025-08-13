import { getBeatmaps } from '../services/api.js';
import { createBeatmapCard } from '../components/BeatmapCard.js';
import { renderPagination } from '../components/Pagination.js';

let searchTimeout;
let currentSearchTerm = '';

export function createBeatmapsView() {
    const view = document.createElement('div');
    view.id = 'beatmaps-view';
    view.className = 'view';
    view.innerHTML = `
        <h2>All Beatmaps</h2>
        <div class="search-container">
            <input type="search" id="beatmaps-search" class="search-input" placeholder="Search by title, artist, mapper...">
        </div>
        <div id="beatmaps-pagination" class="pagination-controls"></div>
        <div id="beatmaps-container"></div>
    `;

    const searchInput = view.querySelector('#beatmaps-search');
    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            currentSearchTerm = searchInput.value;
            loadBeatmaps(view, 1, currentSearchTerm);
        }, 300); // 300ms debounce
    });

    return view;
}

export async function loadBeatmaps(viewElement, page = 1, searchTerm = currentSearchTerm) {
    const container = viewElement.querySelector('#beatmaps-container');
    const paginationContainer = viewElement.querySelector('#beatmaps-pagination');
    const statusMessage = document.getElementById('status-message');
    
    currentSearchTerm = searchTerm;
    statusMessage.textContent = 'Loading beatmap data...';
    container.innerHTML = '';
    paginationContainer.innerHTML = '';

    try {
        const response = await getBeatmaps(page, 50, searchTerm);
        const { beatmaps, total } = response;

        const start = Math.min((page - 1) * 50 + 1, total);
        const end = Math.min(start + beatmaps.length - 1, total);

        statusMessage.textContent = total > 0 ? `Displaying ${start}-${end} of ${total} beatmaps.` : 'No beatmaps found. Try scanning or adjusting your search.';
        
        beatmaps.forEach(beatmap => {
            const card = createBeatmapCard(beatmap);
            container.appendChild(card);
        });

        if (total > 0) {
            renderPagination(paginationContainer, page, total, 50, (newPage) => {
                loadBeatmaps(viewElement, newPage, searchTerm);
            });
        }

    } catch (error) {
        console.error('Error fetching beatmap data:', error);
        statusMessage.textContent = error.message;
    }
}