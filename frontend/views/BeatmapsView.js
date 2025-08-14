import { getBeatmaps, getProgressStatus } from '../services/api.js';
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
    const searchInput = viewElement.querySelector('#beatmaps-search');
    const statusMessage = document.getElementById('status-message');

    // Disable search during sync, but still allow viewing
    try {
        const progress = await getProgressStatus();
        searchInput.disabled = progress.sync.status === 'running';
    } catch (e) {
         statusMessage.textContent = 'Could not get task status. Loading may be incomplete.';
    }

    currentSearchTerm = searchTerm;
    statusMessage.textContent = 'Loading beatmap data...';

    // Don't clear the container if we are just refreshing during a sync on page 1
    const isRefreshingSync = searchInput.disabled && page === 1;
    if (!isRefreshingSync) {
        container.innerHTML = '';
        paginationContainer.innerHTML = '';
    }

    try {
        const response = await getBeatmaps(page, 50, searchTerm);
        const { beatmaps, total } = response;
        
        // If we are refreshing, clear the old content before adding the new
        if (isRefreshingSync) {
            container.innerHTML = '';
            paginationContainer.innerHTML = '';
        }

        const start = Math.min((page - 1) * 50 + 1, total);
        const end = Math.min(start + beatmaps.length - 1, total);
        
        const currentStatus = (await getProgressStatus()).sync;
        if (currentStatus.status !== 'running') {
             statusMessage.textContent = total > 0 ? `Displaying ${start}-${end} of ${total} beatmaps.` : 'No beatmaps found. Try scanning or adjusting your search.';
        }

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
        container.innerHTML = `<p>Error: ${error.message}</p>`;
    }
}