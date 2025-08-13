import { syncBeatmaps, scanReplays } from '../services/api.js';

export function createConfigView() {
    const view = document.createElement('div');
    view.id = 'config-view';
    view.className = 'view';

    view.innerHTML = `
        <h2>Configuration & Maintenance</h2>
        <div id="config-status-message"></div>
        
        <div class="config-action-card">
            <h3>Sync Beatmap Database</h3>
            <p>Parses your osu!.db and all .osu files to build a local database of your beatmaps. This is required for map details and backgrounds to appear correctly. Run this once after adding new maps. This may take some time.</p>
            <button id="sync-beatmaps-button">Start Sync</button>
        </div>

        <div class="config-action-card">
            <h3>Scan New Replays</h3>
            <p>Scans your osu! replays folder for new scores, calculates PP for them if possible, and adds them to the tracker.</p>
            <button id="scan-replays-button-config">Start Scan</button>
        </div>
    `;

    const syncButton = view.querySelector('#sync-beatmaps-button');
    const scanButton = view.querySelector('#scan-replays-button-config');
    const statusMessage = view.querySelector('#config-status-message');

    const setStatus = (message, type = 'info') => {
        statusMessage.textContent = message;
        statusMessage.style.display = 'block';
        statusMessage.className = type; // 'info', 'success', or 'error'
    };

    syncButton.addEventListener('click', async () => {
        setStatus('Syncing beatmap database... This might take a while.', 'info');
        syncButton.disabled = true;
        scanButton.disabled = true;
        try {
            const result = await syncBeatmaps();
            setStatus(result.status || 'Sync complete.', 'success');
            // Notify main.js that data has changed so it can update the player list.
            view.dispatchEvent(new CustomEvent('datachanged', { bubbles: true }));
        } catch (error) {
            console.error('Error during beatmap sync:', error);
            setStatus(`Error: ${error.message}`, 'error');
        } finally {
            syncButton.disabled = false;
            scanButton.disabled = false;
        }
    });

    scanButton.addEventListener('click', async () => {
        setStatus('Scanning for new replays...', 'info');
        syncButton.disabled = true;
        scanButton.disabled = true;
        try {
            const result = await scanReplays();
            setStatus(result.status || 'Scan complete.', 'success');
             // Notify main.js that data has changed so it can update the player list.
            view.dispatchEvent(new CustomEvent('datachanged', { bubbles: true }));
        } catch (error) {
            console.error('Error during replay scan:', error);
            setStatus(`Error: ${error.message}`, 'error');
        } finally {
            syncButton.disabled = false;
            scanButton.disabled = false;
        }
    });

    return view;
}