document.addEventListener('DOMContentLoaded', () => {
    const apiBaseUrl = 'http://127.0.0.1:5000/api';
    const container = document.getElementById('replays-container');
    const scanButton = document.getElementById('scan-button');
    const statusMessage = document.getElementById('status-message');
    let currentlyPlaying = { audio: null, button: null };

    const fetchAndDisplayReplays = async () => {
        statusMessage.textContent = 'Loading replay data...';
        container.innerHTML = '';
        try {
            const replays = await (await fetch(`${apiBaseUrl}/replays`)).json();
            statusMessage.textContent = replays.length > 0 ? `Displaying ${replays.length} scores.` : 'No replays found. Try scanning the folder.';
            displayReplaysAsCards(replays);
        } catch (error) {
            console.error('Error fetching data:', error);
            statusMessage.textContent = `Error: ${error.message}. Is the backend running?`;
        }
    };

    const displayReplaysAsCards = (data) => {
        data.forEach(item => {
            const card = document.createElement('div');
            card.className = 'replay-card';
            const beatmap = item.beatmap || {};

            if (beatmap.folder_name && beatmap.background_file) {
                card.style.backgroundImage = `url(${apiBaseUrl}/songs/${encodeURIComponent(beatmap.folder_name)}/${encodeURIComponent(beatmap.background_file)})`;
            }

            const wrapper = document.createElement('div');
            wrapper.className = 'card-content-wrapper';
            
            const rankEmblem = document.createElement('div');
            rankEmblem.className = 'card-left';
            rankEmblem.innerHTML = `<div class="rank-emblem rank-${item.rank}">${item.rank}</div>`;

            const right = document.createElement('div');
            right.className = 'card-right';
            right.innerHTML = `
                <div>
                    <div class="card-title" title="${beatmap.artist} - ${beatmap.title}">${beatmap.artist} - ${beatmap.title}</div>
                    <div class="card-difficulty" title="[${beatmap.difficulty}] mapped by ${beatmap.creator}">[${beatmap.difficulty}] mapped by ${beatmap.creator}</div>
                    <div class="card-player">Played by ${item.player_name}</div>
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

            const totalHits = item.num_300s + item.num_100s + item.num_50s + item.num_misses;
            const accuracy = totalHits > 0 ? ((item.num_300s * 300 + item.num_100s * 100 + item.num_50s * 50) / (totalHits * 300) * 100).toFixed(2) : "0.00";
            const playedAt = beatmap.last_played_date ? new Date(beatmap.last_played_date).toLocaleDateString() : "Unknown";

            const extraDetails = document.createElement('div');
            extraDetails.className = 'card-extra-details';
            extraDetails.innerHTML = `
                <div class="detail-item"><span class="detail-label">Accuracy</span><span>${accuracy}%</span></div>
                <div class="detail-item"><span class="detail-label">Max Combo</span><span>${item.max_combo}x</span></div>
                <div class="detail-item"><span class="detail-label">Played On</span><span>${playedAt}</span></div>`;

            card.append(wrapper, extraDetails);
            container.appendChild(card);
            
            const playButton = card.querySelector('.play-button');
            card.addEventListener('click', (e) => {
                if(playButton.contains(e.target)) return; // Don't expand if click was on play button
                card.classList.toggle('card-expanded');
            });
            
            if (beatmap.folder_name && beatmap.audio_file) {
                 const audio = new Audio(`${apiBaseUrl}/songs/${encodeURIComponent(beatmap.folder_name)}/${encodeURIComponent(beatmap.audio_file)}`);
                 playButton.addEventListener('click', e => {
                    e.stopPropagation();
                    if(currentlyPlaying.audio === audio && !audio.paused) { audio.pause(); }
                    else { if(currentlyPlaying.audio) { currentlyPlaying.audio.pause(); } audio.currentTime = 0; audio.play(); }
                 });
                 audio.onplay = () => {
                    if (currentlyPlaying.button) currentlyPlaying.button.textContent = '▶';
                    playButton.textContent = '❚❚'; currentlyPlaying = { audio, button: playButton };
                 };
                 audio.onpause = audio.onended = () => {
                    playButton.textContent = '▶'; if (currentlyPlaying.audio === audio) currentlyPlaying = { audio: null, button: null };
                 };
            } else { playButton.disabled = true; }
        });
    };

    scanButton.addEventListener('click', async () => {
        statusMessage.textContent = 'Scanning... this may take a moment.';
        scanButton.disabled = true;
        try {
            const response = await fetch(`${apiBaseUrl}/scan`, { method: 'POST' });
            const result = await response.json();
            statusMessage.textContent = result.status || 'Scan complete.';
            fetchAndDisplayReplays();
        } catch (error) {
            console.error('Error during scan:', error);
            statusMessage.textContent = 'Error during scan.';
        } finally {
            scanButton.disabled = false;
        }
    });

    fetchAndDisplayReplays();
});