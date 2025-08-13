import { getSongFileUrl } from '../services/api.js';

export function createBeatmapCard(beatmap) {
    const card = document.createElement('div');
    card.className = 'beatmap-card';

    if (beatmap.folder_name && beatmap.background_file) {
        const imageUrl = getSongFileUrl(beatmap.folder_name, beatmap.background_file);
        card.style.backgroundImage = `url("${CSS.escape(imageUrl)}")`;
    }

    const mainBpm = beatmap.bpm ? Math.round(beatmap.bpm) : null;
    const minBpm = beatmap.bpm_min ? Math.round(beatmap.bpm_min) : null;
    const maxBpm = beatmap.bpm_max ? Math.round(beatmap.bpm_max) : null;

    let bpmText;
    if (mainBpm) {
        if (minBpm && maxBpm && (maxBpm - minBpm) > 1) {
            bpmText = `${minBpm}-${maxBpm} (${mainBpm}) BPM`;
        } else {
            bpmText = `${mainBpm} BPM`;
        }
    } else {
        bpmText = 'N/A';
    }

    // New structure to match the updated CSS
    card.innerHTML = `
        <div class="card-content-wrapper">
            <div class="card-info">
                <h3 class="card-title" title="${beatmap.artist} - ${beatmap.title}">${beatmap.artist || 'Unknown Artist'} - ${beatmap.title || 'Unknown Title'}</h3>
                <p class="card-subtitle" title="[${beatmap.difficulty}] mapped by ${beatmap.creator}">[${beatmap.difficulty || '?'}] by ${beatmap.creator || 'Unknown Mapper'}</p>
            </div>
            <div class="card-stats">
                <div class="stat-item" title="Circle Size"><span class="label">CS</span><span class="value">${beatmap.cs}</span></div>
                <div class="stat-item" title="Approach Rate"><span class="label">AR</span><span class="value">${beatmap.ar}</span></div>
                <div class="stat-item" title="Overall Difficulty"><span class="label">OD</span><span class="value">${beatmap.od}</span></div>
                <div class="stat-item" title="HP Drain"><span class="label">HP</span><span class="value">${beatmap.hp}</span></div>
                <div class="stat-item bpm-stat" title="Beats Per Minute"><span class="label">♫</span><span class="value">${bpmText}</span></div>
            </div>
        </div>
    `;

    return card;
}