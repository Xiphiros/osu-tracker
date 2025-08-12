document.addEventListener('DOMContentLoaded', () => {
    const apiBaseUrl = 'http://127.0.0.1:5000/api';
    const container = document.getElementById('replays-container');
    const scanButton = document.getElementById('scan-button');
    const statusMessage = document.getElementById('status-message');

    const fetchAndDisplayReplays = async () => {
        statusMessage.textContent = 'Loading replay data...';
        container.innerHTML = ''; // Clear existing cards

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
            
            // Set background image
            if (beatmap.folder_name && beatmap.background_file) {
                // URL encode parts of the path to handle special characters
                const folder = encodeURIComponent(beatmap.folder_name);
                const file = encodeURIComponent(beatmap.background_file);
                card.style.backgroundImage = `url(${apiBaseUrl}/songs/${folder}/${file})`;
            }

            // Create overlay for content
            const overlay = document.createElement('div');
            overlay.className = 'card-overlay';

            const title = document.createElement('h3');
            title.className = 'card-title';
            title.textContent = beatmap.title ? `${beatmap.artist} - ${beatmap.title}` : 'Unknown Beatmap';
            title.title = title.textContent; // Show full title on hover

            const difficulty = document.createElement('p');
            difficulty.className = 'card-difficulty';
            difficulty.textContent = beatmap.difficulty || 'N/A';

            const footer = document.createElement('div');
            footer.className = 'card-footer';

            const scoreInfo = document.createElement('div');
            const score = document.createElement('p');
            score.className = 'card-score';
            score.textContent = `${item.total_score.toLocaleString()}`;

            const judgements = document.createElement('p');
            judgements.className = 'card-judgements';
            judgements.textContent = `300:${item.num_300s} 100:${item.num_100s} 50:${item.num_50s} X:${item.num_misses}`;
            
            scoreInfo.appendChild(score);
            scoreInfo.appendChild(judgements);

            footer.appendChild(scoreInfo);

            // Add audio player if audio file exists
            if (beatmap.folder_name && beatmap.audio_file) {
                const audio = document.createElement('audio');
                audio.controls = true;
                audio.className = 'card-audio-player';
                const folder = encodeURIComponent(beatmap.folder_name);
                const file = encodeURIComponent(beatmap.audio_file);
                audio.src = `${apiBaseUrl}/songs/${folder}/${file}`;
                footer.appendChild(audio);
            }
            
            overlay.appendChild(title);
            overlay.appendChild(difficulty);
            overlay.appendChild(footer);
            card.appendChild(overlay);
            container.appendChild(card);
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