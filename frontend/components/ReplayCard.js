import { getSongFileUrl } from '../services/api.js';
import { getModsFromInt } from '../utils/mods.js';
import { playAudio } from '../utils/audioPlayer.js';

// Helper function for secure element creation
function createElement(tag, classNames = [], textContent = '') {
    const el = document.createElement(tag);
    if (classNames.length) el.classList.add(...classNames);
    if (textContent) el.textContent = textContent;
    return el;
}

export function createReplayCard(item) {
    const card = createElement('div', ['replay-card']);
    const beatmap = item.beatmap || {};

    if (beatmap.folder_name && beatmap.background_file) {
        const imageUrl = getSongFileUrl(beatmap.folder_name, beatmap.background_file);
        card.style.backgroundImage = `url("${CSS.escape(imageUrl)}")`;
    }

    const mods = getModsFromInt(item.mods_used);
    const isSilverRank = (item.rank === 'S' || item.rank === 'SS') && (mods.includes('HD') || mods.includes('FL'));

    const wrapper = createElement('div', ['card-content-wrapper']);

    const rankEmblemContainer = createElement('div', ['card-left']);
    const rankEmblem = createElement('div', ['rank-emblem', `rank-${item.rank}`], item.rank || 'N/A');
    if (isSilverRank) rankEmblem.classList.add('rank-silver');
    rankEmblemContainer.appendChild(rankEmblem);

    const right = createElement('div', ['card-right']);
    const rightTop = createElement('div'); // container for title, diff, stats

    const title = createElement('div', ['card-title'], `${beatmap.artist || 'Unknown Artist'} - ${beatmap.title || 'Unknown Title'}`);
    title.title = `${beatmap.artist} - ${beatmap.title}`;
    const difficulty = createElement('div', ['card-difficulty'], `[${beatmap.difficulty || '?'}] mapped by ${beatmap.creator || 'Unknown Mapper'}`);
    difficulty.title = `[${beatmap.difficulty}] mapped by ${beatmap.creator}`;
    const player = createElement('div', ['card-player'], `Played by ${item.player_name || 'Unknown Player'}`);

    // Stats (Stars, Aim/Speed, BPM)
    const statsContainer = createElement('div', ['card-stats']);
    const starsStat = createElement('span', ['stat-stars'], `★ ${item.stars ? item.stars.toFixed(2) : 'N/A'}`);
    statsContainer.appendChild(starsStat);

    const aimValue = item.aim ? item.aim.toFixed(2) : null;
    const speedValue = item.speed ? item.speed.toFixed(2) : null;
    if (aimValue && speedValue) {
        const aimStat = createElement('span', ['stat-skill', 'stat-aim'], `🎯 ${aimValue}`);
        aimStat.title = `Aim Difficulty: ${aimValue}`;
        const speedStat = createElement('span', ['stat-skill', 'stat-speed'], `⚡ ${speedValue}`);
        speedStat.title = `Speed Difficulty: ${speedValue}`;
        statsContainer.append(aimStat, speedStat);
    }

    const mainBpm = beatmap.bpm ? Math.round(beatmap.bpm) : null;
    const minBpm = beatmap.bpm_min ? Math.round(beatmap.bpm_min) : null;
    const maxBpm = beatmap.bpm_max ? Math.round(beatmap.bpm_max) : null;
    let bpmText = mainBpm ? (minBpm && maxBpm && (maxBpm - minBpm) > 1 ? `${minBpm}-${maxBpm} (${mainBpm})` : `${mainBpm}`) : 'N/A';
    const bpmStat = createElement('span', ['stat-bpm'], `♫ ${bpmText} BPM`);
    statsContainer.appendChild(bpmStat);
    rightTop.append(title, difficulty, player, statsContainer);

    // Footer (Score, Judgements, Controls)
    const footer = createElement('div', ['card-footer']);
    const scoreContainer = createElement('div');
    const scoreDisplay = createElement('div', ['card-score'], item.total_score.toLocaleString());
    const judgements = createElement('div', ['card-judgements'], `300:${item.num_300s} 100:${item.num_100s} 50:${item.num_50s} X:${item.num_misses}`);
    scoreContainer.append(scoreDisplay, judgements);

    const footerControls = createElement('div', ['footer-controls']);
    const modsContainer = createElement('div', ['card-mods']);
    if (mods.length > 0) {
        mods.forEach(mod => {
            modsContainer.appendChild(createElement('span', ['mod-badge'], mod));
        });
    }
    const playButton = createElement('button', ['play-button'], '▶');
    const expandIndicator = createElement('div', ['expand-indicator'], '▼');
    footerControls.append(modsContainer, playButton, expandIndicator);
    footer.append(scoreContainer, footerControls);
    right.append(rightTop, footer);
    wrapper.append(rankEmblemContainer, right);

    // Extra Details (collapsible part)
    const extraDetails = createElement('div', ['card-extra-details']);
    const createDetailItem = (label, value) => {
        const itemEl = createElement('div', ['detail-item']);
        const labelSpan = createElement('span', ['detail-label'], label);
        const valueSpan = createElement('span', [], value);
        itemEl.append(labelSpan, valueSpan);
        return itemEl;
    };

    const totalHits = item.num_300s + item.num_100s + item.num_50s + item.num_misses;
    const accuracy = totalHits > 0 ? ((item.num_300s * 300 + item.num_100s * 100 + item.num_50s * 50) / (totalHits * 300) * 100).toFixed(2) : "0.00";
    const playedAt = item.played_at ? new Date(item.played_at).toLocaleDateString() : "Unknown";

    extraDetails.append(
        createDetailItem('Accuracy', `${accuracy}%`),
        createDetailItem('Performance', item.pp ? `${item.pp.toFixed(2)}pp` : 'N/A'),
        createDetailItem('Star Rating', item.stars ? `★ ${item.stars.toFixed(2)}` : 'N/A'),
        createDetailItem('Max Combo', `${item.max_combo || 0}x / ${item.map_max_combo || '?'}x`),
        createDetailItem('Played On', playedAt)
    );

    card.append(wrapper, extraDetails);

    // Event Listeners
    card.addEventListener('click', (e) => {
        if (playButton.contains(e.target)) return;
        card.classList.toggle('card-expanded');
    });

    if (beatmap.folder_name && beatmap.audio_file) {
        const audioUrl = getSongFileUrl(beatmap.folder_name, beatmap.audio_file);
        playButton.addEventListener('click', e => {
            e.stopPropagation();
            playAudio(
                audioUrl,
                () => { playButton.textContent = '❚❚'; }, // onPlay
                () => { playButton.textContent = '▶'; }  // onEnd / onPause
            );
        });
    } else {
        playButton.disabled = true;
    }

    return card;
}