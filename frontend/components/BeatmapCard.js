import { getSongFileUrl } from '../services/api.js';
import { playAudio } from '../utils/audioPlayer.js';

export function createBeatmapCard(beatmap) {
    const card = document.createElement('div');
    card.className = 'beatmap-card';

    if (beatmap.folder_name && beatmap.background_file) {
        const imageUrl = getSongFileUrl(beatmap.folder_name, beatmap.background_file);
        card.style.backgroundImage = `url("${CSS.escape(imageUrl)}")`;
        card.classList.add('has-bg');
    }

    const mainBpm = beatmap.bpm ? Math.round(beatmap.bpm) : null;
    const minBpm = beatmap.bpm_min ? Math.round(beatmap.bpm_min) : null;
    const maxBpm = beatmap.bpm_max ? Math.round(beatmap.bpm_max) : null;
    const starsText = beatmap.stars ? beatmap.stars.toFixed(2) : 'N/A';

    let bpmText;
    if (mainBpm) {
        if (minBpm && maxBpm && (maxBpm - minBpm) > 1) {
            bpmText = `${minBpm}-${maxBpm} (${mainBpm})`;
        } else {
            bpmText = `${mainBpm}`;
        }
    } else {
        bpmText = 'N/A';
    }

    card.innerHTML = `
        <div class="card-content-wrapper">
            <div class="card-info">
                <div class="card-buttons">
                    <button class="play-button card-button">▶</button>
                    <button class="open-button card-button" title="Open in osu! client"><span class="open-button-icon"></span></button>
                </div>
                <div class="card-text-content">
                    <h3 class="card-title" title="${beatmap.artist} - ${beatmap.title}">${beatmap.artist || 'Unknown Artist'} - ${beatmap.title || 'Unknown Title'}</h3>
                    <p class="card-subtitle" title="[${beatmap.difficulty}] mapped by ${beatmap.creator}">[${beatmap.difficulty || '?'}] by ${beatmap.creator || 'Unknown Mapper'}</p>
                </div>
            </div>
            <div class="card-stats">
                <div class="stat-item" title="Circle Size"><span class="label">CS</span><span class="value">${beatmap.cs}</span></div>
                <div class="stat-item" title="Approach Rate"><span class="label">AR</span><span class="value">${beatmap.ar}</span></div>
                <div class="stat-item" title="Overall Difficulty"><span class="label">OD</span><span class="value">${beatmap.od}</span></div>
                <div class="stat-item" title="HP Drain"><span class="label">HP</span><span class="value">${beatmap.hp}</span></div>
                <div class="card-footer-stats">
                    <div class="stat-item" title="Star Rating"><span class="label">★</span><span class="value">${starsText}</span></div>
                    <div class="stat-item" title="Beats Per Minute"><span class="label">♫</span><span class="value">${bpmText}</span></div>
                </div>
            </div>
        </div>
    `;

    const playButton = card.querySelector('.play-button');
    if (beatmap.folder_name && beatmap.audio_file) {
        const audioUrl = getSongFileUrl(beatmap.folder_name, beatmap.audio_file);
        playButton.addEventListener('click', (e) => {
            e.stopPropagation(); // prevent any card-level click events
            playAudio(
                audioUrl,
                () => { playButton.textContent = '❚❚'; }, // onPlay
                () => { playButton.textContent = '▶'; }  // onEnd
            );
        });
    } else {
        playButton.disabled = true;
    }

    const openButton = card.querySelector('.open-button');
    if (beatmap.beatmap_id && beatmap.beatmap_id > 0) {
        openButton.addEventListener('click', (e) => {
            e.stopPropagation();
            window.open(`osu://b/${beatmap.beatmap_id}`, '_blank');
        });
    } else {
        openButton.disabled = true;
    }

    return card;
}