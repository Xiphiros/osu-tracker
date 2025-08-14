import { getSongFileUrl } from '../services/api.js';
import { playAudio } from '../utils/audioPlayer.js';

// Helper function to create an element with classes and text content securely
function createElement(tag, classNames = [], textContent = '') {
    const el = document.createElement(tag);
    if (classNames.length) el.classList.add(...classNames);
    if (textContent) el.textContent = textContent;
    return el;
}

export function createBeatmapCard(beatmap) {
    const card = createElement('div', ['beatmap-card']);

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

    // --- Build DOM manually to prevent XSS ---
    const wrapper = createElement('div', ['card-content-wrapper']);
    const cardInfo = createElement('div', ['card-info']);

    const playButton = createElement('button', ['play-button'], '▶');
    playButton.title = 'Preview Audio';

    const copyButton = createElement('button', ['copy-button'], '📋');
    copyButton.title = 'Copy Search String';

    const textContentDiv = createElement('div', ['card-text-content']);
    const title = createElement('h3', ['card-title'], `${beatmap.artist || 'Unknown Artist'} - ${beatmap.title || 'Unknown Title'}`);
    title.title = `${beatmap.artist} - ${beatmap.title}`;
    const subtitle = createElement('p', ['card-subtitle'], `[${beatmap.difficulty || '?'}] by ${beatmap.creator || 'Unknown Mapper'}`);
    subtitle.title = `[${beatmap.difficulty}] mapped by ${beatmap.creator}`;
    textContentDiv.append(title, subtitle);

    cardInfo.append(playButton, copyButton, textContentDiv);

    const cardStats = createElement('div', ['card-stats']);
    const createStatItem = (label, value, titleAttr) => {
        const item = createElement('div', ['stat-item']);
        item.title = titleAttr;
        const labelSpan = createElement('span', ['label'], label);
        const valueSpan = createElement('span', ['value'], value);
        item.append(labelSpan, valueSpan);
        return item;
    };
    cardStats.append(
        createStatItem('CS', beatmap.cs, 'Circle Size'),
        createStatItem('AR', beatmap.ar, 'Approach Rate'),
        createStatItem('OD', beatmap.od, 'Overall Difficulty'),
        createStatItem('HP', beatmap.hp, 'HP Drain')
    );

    const footerStats = createElement('div', ['card-footer-stats']);
    const starsStat = createStatItem('★', starsText, 'Star Rating');
    footerStats.appendChild(starsStat);

    const aimValue = beatmap.aim ? beatmap.aim.toFixed(2) : null;
    const speedValue = beatmap.speed ? beatmap.speed.toFixed(2) : null;
    if (aimValue && speedValue) {
        const aimStat = createStatItem('🎯', aimValue, 'Aim Difficulty');
        aimStat.classList.add('stat-aim');
        const speedStat = createStatItem('⚡', speedValue, 'Speed Difficulty');
        speedStat.classList.add('stat-speed');
        footerStats.append(aimStat, speedStat);
    }

    const bpmStat = createStatItem('♫', bpmText, 'Beats Per Minute');
    footerStats.appendChild(bpmStat);
    cardStats.appendChild(footerStats);

    wrapper.append(cardInfo, cardStats);
    card.appendChild(wrapper);

    // --- Event Listeners ---
    if (beatmap.folder_name && beatmap.audio_file) {
        const audioUrl = getSongFileUrl(beatmap.folder_name, beatmap.audio_file);
        playButton.addEventListener('click', (e) => {
            e.stopPropagation();
            playAudio(
                audioUrl,
                () => { playButton.textContent = '❚❚'; }, // onPlay
                () => { playButton.textContent = '▶'; }  // onEnd
            );
        });
    } else {
        playButton.disabled = true;
    }

    copyButton.addEventListener('click', (e) => {
        e.stopPropagation();
        const searchString = `${beatmap.artist} ${beatmap.title} ${beatmap.difficulty} ${beatmap.creator}`;
        navigator.clipboard.writeText(searchString).then(() => {
            const originalText = copyButton.textContent;
            copyButton.textContent = '✅';
            setTimeout(() => {
                copyButton.textContent = originalText;
            }, 1500);
        }).catch(err => {
            console.error('Failed to copy text: ', err);
        });
    });

    return card;
}