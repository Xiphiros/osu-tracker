import { syncBeatmaps, scanReplays, getProgressStatus } from '../services/api.js';

let progressInterval = null;

function stopProgressPolling() {
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
}

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
            <div class="progress-container" id="sync-progress-container">
                <progress id="sync-progress" class="progress-bar" value="0" max="100"></progress>
                <span id="sync-progress-text" class="progress-text"></span>
            </div>
        </div>

        <div class="config-action-card">
            <h3>Scan New Replays</h3>
            <p>Scans your osu! replays folder for new scores, calculates PP for them if possible, and adds them to the tracker.</p>
            <button id="scan-replays-button-config">Start Scan</button>
            <div class="progress-container" id="scan-progress-container">
                <progress id="scan-progress" class="progress-bar" value="0" max="100"></progress>
                <span id="scan-progress-text" class="progress-text"></span>
            </div>
        </div>
    `;

    const syncButton = view.querySelector('#sync-beatmaps-button');
    const scanButton = view.querySelector('#scan-replays-button-config');
    const statusMessage = view.querySelector('#config-status-message');

    const syncProgressContainer = view.querySelector('#sync-progress-container');
    const syncProgressBar = view.querySelector('#sync-progress');
    const syncProgressText = view.querySelector('#sync-progress-text');

    const scanProgressContainer = view.querySelector('#scan-progress-container');
    const scanProgressBar = view.querySelector('#scan-progress');
    const scanProgressText = view.querySelector('#scan-progress-text');
    
    const setButtonsDisabled = (disabled) => {
        syncButton.disabled = disabled;
        scanButton.disabled = disabled;
    };

    const setStatus = (message, type = 'info') => {
        statusMessage.textContent = message;
        statusMessage.style.display = 'block';
        statusMessage.className = type;
    };

    const startPolling = () => {
        stopProgressPolling(); // Ensure no multiple intervals are running
        
        progressInterval = setInterval(async () => {
            try {
                const progress = await getProgressStatus();
                
                // Update Sync Progress
                const syncData = progress.sync;
                syncProgressContainer.style.display = (syncData.status === 'running') ? 'block' : 'none';
                if (syncData.status === 'running') {
                    syncProgressBar.value = syncData.current;
                    syncProgressBar.max = syncData.total || 100;
                    syncProgressText.textContent = `${syncData.message} (${syncData.current} / ${syncData.total || '?'})`;
                }
                
                // Update Scan Progress
                const scanData = progress.scan;
                scanProgressContainer.style.display = (scanData.status === 'running') ? 'block' : 'none';
                if (scanData.status === 'running') {
                    scanProgressBar.value = scanData.current;
                    scanProgressBar.max = scanData.total || 100;
                    scanProgressText.textContent = `${scanData.message} (${scanData.current} / ${scanData.total || '?'})`;
                }

                // Check for completion or error
                if (syncData.status !== 'running' && scanData.status !== 'running') {
                    stopProgressPolling();
                    setButtonsDisabled(false);
                    
                    if (syncData.status === 'complete' || scanData.status === 'complete') {
                        setStatus(syncData.message || scanData.message, 'success');
                        view.dispatchEvent(new CustomEvent('datachanged', { bubbles: true }));
                    } else if (syncData.status === 'error' || scanData.status === 'error') {
                        setStatus(syncData.message || scanData.message, 'error');
                    }
                }

            } catch (error) {
                setStatus('Could not retrieve progress. Connection lost.', 'error');
                stopProgressPolling();
                setButtonsDisabled(false);
            }
        }, 500);
    };

    syncButton.addEventListener('click', async () => {
        statusMessage.style.display = 'none';
        setButtonsDisabled(true);
        syncProgressContainer.style.display = 'block';
        syncProgressBar.value = 0;
        syncProgressText.textContent = 'Starting sync...';

        try {
            await syncBeatmaps();
            startPolling();
        } catch (error) {
            setStatus(`Error starting sync: ${error.message}`, 'error');
            setButtonsDisabled(false);
        }
    });

    scanButton.addEventListener('click', async () => {
        statusMessage.style.display = 'none';
        setButtonsDisabled(true);
        scanProgressContainer.style.display = 'block';
        scanProgressBar.value = 0;
        scanProgressText.textContent = 'Starting scan...';
        try {
            await scanReplays();
            startPolling();
        } catch (error) {
            setStatus(`Error starting scan: ${error.message}`, 'error');
            setButtonsDisabled(false);
        }
    });

    return view;
}