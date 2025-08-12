import { getSongFileUrl } from '../services/api.js';
import { getModsFromInt } from '../utils/mods.js';

let currentlyPlaying = { audio: null, button: null };

export function createReplayCard(item) {
    const card = document.createElement('div');
    card.className = 'replay-card';
    const beatmap = item.beatmap || {};

    if (beatmap.folder_name && beatmap.background_file) {
        card.style.backgroundImage = `url(${getSongFileUrl(beatmap.folder_name, beatmap.background_file)})`;
    }

    const mods = getModsFromInt(item.mods_used);
    const isSilverRank = (item.rank === 'S' || item.rank === 'SS') && (mods.includes('HD') || mods.includes('FL'));

    const wrapper = document.createElement('div');
    wrapper.className = 'card-content-wrapper';

    const rankEmblem = document.createElement('div');
    rankEmblem.className = 'card-left';
    rankEmblem.innerHTML = `<div class="rank-emblem rank-${item.rank} ${isSilverRank ? 'rank-silver' : ''}">${item.rank || 'N/A'}</div>`;

    const right = document.createElement('div');
    right.className = 'card-right';
    right.innerHTML = `
        <div>
            <div class="card-title" title="${beatmap.artist} - ${beatmap.title}">${beatmap.artist || 'Unknown Artist'} - ${beatmap.title || 'Unknown Title'}</div>
            <div class="card-difficulty" title="[${beatmap.difficulty}] mapped by ${beatmap.creator}">[${beatmap.difficulty || '?'}] mapped by ${beatmap.creator || 'Unknown Mapper'}</div>
            <div class="card-player">Played by ${item.player_name || 'Unknown Player'}</div>
        </div>
        <div class="card-footer">
            <div>
                <div class="card-score">${item.total_score.toLocaleString()}</div>
                <div class="card-judgements">300:${item.num_300s} 100:${item.num_100s} 50:${item.num_50s} X:${item.num_misses}</div>
            </div>
            <div class="footer-controls">
                <button class="play-button">▶</button>
                <div class="expand-indicator">▼</div>
            </div>
        </div>`;
    wrapper.append(rankEmblem, right);
    
    const modsContainer = document.createElement('div');
    modsContainer.className = 'card-mods';
    if (mods.length > 0) {
        mods.forEach(mod => {
            const modBadge = document.createElement('span');
            modBadge.className = 'mod-badge';
            modBadge.textContent = mod;
            modsContainer.appendChild(modBadge);
        });
    }

    // Add mods container to footer controls
    const footerControls = right.querySelector('.footer-controls');
    footerControls.prepend(modsContainer);


    const totalHits = item.num_300s + item.num_100s + item.num_50s + item.num_misses;
    const accuracy = totalHits > 0 ? ((item.num_300s * 300 + item.num_100s * 100 + item.num_50s * 50) / (totalHits * 300) * 100).toFixed(2) : "0.00";
    const playedAt = item.played_at ? new Date(item.played_at).toLocaleDateString() : "Unknown";

    const extraDetails = document.createElement('div');
    extraDetails.className = 'card-extra-details';

    const createDetailItem = (label, value) => {
        const itemEl = document.createElement('div');
        itemEl.className = 'detail-item';
        itemEl.innerHTML = `<span class="detail-label">${label}</span><span>${value}</span>`;
        return itemEl;
    };

    extraDetails.appendChild(createDetailItem('Accuracy', `${accuracy}%`));
    extraDetails.appendChild(createDetailItem('Performance', item.pp ? `${item.pp.toFixed(2)}pp` : 'N/A'));
    extraDetails.appendChild(createDetailItem('Star Rating', item.stars ? `★ ${item.stars.toFixed(2)}` : 'N/A'));
    extraDetails.appendChild(createDetailItem('Max Combo', `${item.max_combo || 0}x / ${item.map_max_combo || '?'}x`));
    extraDetails.appendChild(createDetailItem('Played On', playedAt));

    card.append(wrapper, extraDetails);

    const playButton = card.querySelector('.play-button');
    card.addEventListener('click', (e) => {
        if(playButton.contains(e.target)) return;
        card.classList.toggle('card-expanded');
    });

    if (beatmap.folder_name && beatmap.audio_file) {
        const audioUrl = getSongFileUrl(beatmap.folder_name, beatmap.audio_file);
        const audio = new Audio(audioUrl);

        playButton.addEventListener('click', e => {
            e.stopPropagation();
            if (currentlyPlaying.audio === audio && !audio.paused) {
                audio.pause();
            } else {
                if (currentlyPlaying.audio) {
                    currentlyPlaying.audio.pause();
                }
                audio.currentTime = 0;
                audio.play();
            }
        });

        audio.onplay = () => {
            if (currentlyPlaying.button) currentlyPlaying.button.textContent = '▶';
            playButton.textContent = '❚❚';
            currentlyPlaying = { audio, button: playButton };
        };

        audio.onpause = audio.onended = () => {
            playButton.textContent = '▶';
            if (currentlyPlaying.audio === audio) {
                currentlyPlaying = { audio: null, button: null };
            }
        };
    } else {
        playButton.disabled = true;
    }

    return card;
}