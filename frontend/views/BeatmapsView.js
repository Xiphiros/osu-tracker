import { getBeatmaps } from '../services/api.js';
import { createBeatmapCard } from '../components/BeatmapCard.js';

export function createBeatmapsView() {
    const view = document.createElement('div');
    view.id = 'beatmaps-view';
    view.className = 'view';
    view.innerHTML = `
        <h2>All Beatmaps</h2>
        <div id="beatmaps-container"></div>
    `;
    return view;
}

export async function loadBeatmaps(viewElement) {
    const container = viewElement.querySelector('#beatmaps-container');
    const statusMessage = document.getElementById('status-message');
    
    statusMessage.textContent = 'Loading beatmap data...';
    container.innerHTML = '';

    try {
        const beatmaps = await getBeatmaps();
        // Simple sort by artist then title
        beatmaps.sort((a, b) => {
            if (a.artist.toLowerCase() < b.artist.toLowerCase()) return -1;
            if (a.artist.toLowerCase() > b.artist.toLowerCase()) return 1;
            if (a.title.toLowerCase() < b.title.toLowerCase()) return -1;
            if (a.title.toLowerCase() > b.title.toLowerCase()) return 1;
            return 0;
        });

        statusMessage.textContent = beatmaps.length > 0 ? `Displaying ${beatmaps.length} beatmaps.` : 'No beatmaps found. Try scanning.';
        
        beatmaps.forEach(beatmap => {
            const card = createBeatmapCard(beatmap);
            container.appendChild(card);
        });

    } catch (error) {
        console.error('Error fetching beatmap data:', error);
        statusMessage.textContent = error.message;
    }
}