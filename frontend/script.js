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
            const response = await fetch(`${apiBaseUrl}/replays`);
            if (!response.ok) throw new Error('Failed to fetch replays.');
            const replays = await response.json();

            if (replays.length === 0) {
                statusMessage.textContent = 'No replays found. Try scanning the folder.';
                return;
            }
            statusMessage.textContent = `Displaying ${replays.length} scores.`;
            displayReplaysAsCards(replays);
        } catch (error) {
            console.error('Error fetching data:', error);
            statusMessage.textContent = `Error: ${error.message}. Is the backend server running?`;
        }
    };

    const displayReplaysAsCards = (data) => {
        data.forEach(item => {
            const card = document.createElement('div');
            card.className = 'replay-card';
            const beatmap = item.beatmap || {};
            if (beatmap.folder_name && beatmap.background_file) {
                const folder = encodeURIComponent(beatmap.folder_name);
                const file = encodeURIComponent(beatmap.background_file);
                card.style.backgroundImage = `url(${apiBaseUrl}/songs/${folder}/${file})`;
            }

            const wrapper = document.createElement('div');
            wrapper.className = 'card-content-wrapper';

            // Left Side (Rank)
            const left = document.createElement('div');
            left.className = 'card-left';
            const rankEmblem = document.createElement('div');
            rankEmblem.className = `rank-emblem rank-${item.rank}`;
            rankEmblem.textContent = item.rank;
            left.appendChild(rankEmblem);

            // Right Side (Details)
            const right = document.createElement('div');
            right.className = 'card-right';

            const infoTop = document.createElement('div');
            const title = document.createElement('div');
            title.className = 'card-title';
            title.textContent = beatmap.title ? `${beatmap.artist} - ${beatmap.title}` : 'Unknown Beatmap';
            const difficulty = document.createElement('div');
            difficulty.className = 'card-difficulty';
            difficulty.textContent = `[${beatmap.difficulty}] mapped by ${beatmap.creator}`;
            const player = document.createElement('div');
            player.className = 'card-player';
            player.textContent = `Played by ${item.player_name}`;
            infoTop.append(title, difficulty, player);
            
            const infoBottom = document.createElement('div');
            infoBottom.className = 'card-footer';
            
            const scoreDetails = document.createElement('div');
            const score = document.createElement('div');
            score.className = 'card-score';
            score.textContent = item.total_score.toLocaleString();
            const judgements = document.createElement('div');
            judgements.className = 'card-judgements';
            judgements.textContent = `300:${item.num_300s} 100:${item.num_100s} 50:${item.num_50s} X:${item.num_misses}`;
            scoreDetails.append(score, judgements);

            const playButton = document.createElement('button');
            playButton.className = 'play-button';
            playButton.textContent = '▶';
            
            infoBottom.append(scoreDetails, playButton);
            right.append(infoTop, infoBottom);

            wrapper.append(left, right);
            card.appendChild(wrapper);
            container.appendChild(card);
            
            // Audio Logic
            if (beatmap.folder_name && beatmap.audio_file) {
                const audio = new Audio();
                const folder = encodeURIComponent(beatmap.folder_name);
                const file = encodeURIComponent(beatmap.audio_file);
                audio.src = `${apiBaseUrl}/songs/${folder}/${file}`;

                playButton.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (currentlyPlaying.audio === audio && !audio.paused) {
                        audio.pause();
                    } else {
                        if (currentlyPlaying.audio) currentlyPlaying.audio.pause();
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
                playButton.style.opacity = '0.3';
            }
        });
    };

    scanButton.addEventListener('click', async () => {
        statusMessage.textContent = 'Scanning... this may take a moment.';
        scanButton.disabled = true;
        try {
            const response = await fetch(`${apiBaseUrl}/scan`, { method: 'POST' });
            const result = await response.json();
            statusMessage.textContent = result.status || 'Scan complete.';
            // Refresh the data after scanning
            fetchAndDisplayReplays();
        } catch (error) {
            console.error('Error during scan:', error);
            statusMessage.textContent = 'Error during scan.';
        } finally {
            scanButton.disabled = false;
        }
    });

    // Initial data load when the page is opened
    fetchAndDisplayReplays();
});