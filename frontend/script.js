document.addEventListener('DOMContentLoaded', () => {
    const apiBaseUrl = 'http://127.0.0.1:5000/api';
    const replaysTbody = document.getElementById('replays-tbody');
    const scanButton = document.getElementById('scan-button');
    const statusMessage = document.getElementById('status-message');

    const fetchAndDisplayReplays = async () => {
        statusMessage.textContent = 'Loading replay data...';
        replaysTbody.innerHTML = ''; // Clear existing table data

        try {
            // 1. Fetch all replay scores
            const replayResponse = await fetch(`${apiBaseUrl}/replays`);
            if (!replayResponse.ok) throw new Error('Failed to fetch replays.');
            const replays = await replayResponse.json();

            if (replays.length === 0) {
                statusMessage.textContent = 'No replays found. Try scanning the folder.';
                return;
            }

            statusMessage.textContent = `Found ${replays.length} replays. Fetching beatmap details...`;

            // 2. Fetch beatmap details for each replay concurrently
            const replayPromises = replays.map(async (replay) => {
                const beatmapResponse = await fetch(`${apiBaseUrl}/beatmap/${replay.beatmap_md5}`);
                if (beatmapResponse.ok) {
                    const beatmap = await beatmapResponse.json();
                    return { ...replay, beatmap }; // Combine replay and beatmap data
                }
                return replay; // Return replay data even if beatmap fetch fails
            });

            const combinedData = await Promise.all(replayPromises);

            // 3. Populate the table
            populateTable(combinedData);
            statusMessage.textContent = `Displaying ${combinedData.length} scores.`;

        } catch (error) {
            console.error('Error fetching data:', error);
            statusMessage.textContent = `Error: ${error.message}. Is the backend server running?`;
        }
    };

    const populateTable = (data) => {
        data.forEach(item => {
            const row = document.createElement('tr');

            const beatmapInfo = item.beatmap ? `${item.beatmap.artist} - ${item.beatmap.title}` : 'Unknown Beatmap';
            const difficulty = item.beatmap ? item.beatmap.difficulty : 'N/A';
            const difficultyStats = item.beatmap ? `${item.beatmap.ar}/${item.beatmap.od}/${item.beatmap.cs}/${item.beatmap.hp}` : 'N/A';
            const bpm = item.beatmap ? item.beatmap.bpm : 'N/A';
            const judgements = `${item.num_300s}/${item.num_100s}/${item.num_50s}/${item.num_misses}`;
            
            row.innerHTML = `
                <td>${beatmapInfo}</td>
                <td>${difficulty}</td>
                <td>${item.total_score.toLocaleString()}</td>
                <td>${judgements}</td>
                <td>${item.player_name}</td>
                <td>${difficultyStats}</td>
                <td>${bpm}</td>
            `;
            replaysTbody.appendChild(row);
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