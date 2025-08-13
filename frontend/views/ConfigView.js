import { syncBeatmaps, scanReplays, getProgressStatus, getConfig, saveConfig, getPlayers } from '../services/api.js';

let progressInterval = null;
let lastSyncStatus = 'idle';
let lastScanStatus = 'idle';

function stopProgressPolling() {
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
}

async function loadConfigData(view) {
    const folderInput = view.querySelector('#osu-folder-input');
    const playerSelect = view.querySelector('#default-player-select');
    
    try {
        const [config, players] = await Promise.all([getConfig(), getPlayers()]);
        
        folderInput.value = config.osu_folder || '';
        
        playerSelect.innerHTML = '<option value="">None</option>';
        players.forEach(player => {
            const isSelected = player === config.default_player;
            playerSelect.innerHTML += `<option value="${player}" ${isSelected ? 'selected' : ''}>${player}</option>`;
        });
        
    } catch (error) {
        console.error("Failed to load config data:", error);
        const statusMessage = view.querySelector('#config-status-message');
        statusMessage.textContent = `Error loading settings: ${error.message}`;
        statusMessage.className = 'error';
        statusMessage.style.display = 'block';
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
            <h3>Application Settings</h3>
            <div class="form-group">
                <label for="osu-folder-input">osu! Folder Path</label>
                <input type="text" id="osu-folder-input" placeholder="e.g., C:/Users/YourUser/AppData/Local/osu!">
                <small>The absolute path to your osu! installation directory. A restart is required for this to take full effect.</small>
            </div>
            <div class="form-group">
                <label for="default-player-select">Default Player</label>
                <select id="default-player-select"></select>
                <small>The player profile to load when the application starts.</small>
            </div>
            <button id="save-config-button">Save Settings</button>
        </div>
        
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

    // Attach event listeners after innerHTML is set
    view.addEventListener('viewactivated', () => loadConfigData(view));
    
    const saveButton = view.querySelector('#save-config-button');
    const statusMessage = view.querySelector('#config-status-message');

    saveButton.addEventListener('click', async () => {
        const osuFolder = view.querySelector('#osu-folder-input').value;
        const defaultPlayer = view.querySelector('#default-player-select').value;
        
        saveButton.disabled = true;
        saveButton.textContent = 'Saving...';
        statusMessage.style.display = 'none';

        try {
            await saveConfig({
                "osu_folder": osuFolder,
                "default_player": defaultPlayer
            });
            setStatus('Settings saved successfully!', 'success');
            // Notify other parts of the app that data (like default player) might have changed
            view.dispatchEvent(new CustomEvent('datachanged', { bubbles: true }));
        } catch (error) {
            setStatus(`Error saving settings: ${error.message}`, 'error');
        } finally {
            saveButton.disabled = false;
            saveButton.textContent = 'Save Settings';
        }
    });

    const syncButton = view.querySelector('#sync-beatmaps-button');
    const scanButton = view.querySelector('#scan-replays-button-config');

    const syncProgressContainer = view.querySelector('#sync-progress-container');
    const syncProgressBar = view.querySelector('#sync-progress');
    const syncProgressText = view.querySelector('#sync-progress-text');

    const scanProgressContainer = view.querySelector('#scan-progress-container');
    const scanProgressBar = view.querySelector('#scan-progress');
    const scanProgressText = view.querySelector('#scan-progress-text');
    
    const setButtonsDisabled = (disabled) => {
        syncButton.disabled = disabled;
        scanButton.disabled = disabled;
        saveButton.disabled = disabled;
    };

    const setStatus = (message, type = 'info') => {
        statusMessage.textContent = message;
        statusMessage.style.display = 'block';
        statusMessage.className = type;
    };

    const startPolling = () => {
        stopProgressPolling();
        lastSyncStatus = 'running';
        lastScanStatus = 'running';
        
        progressInterval = setInterval(async () => {
            try {
                const progress = await getProgressStatus();
                const syncData = progress.sync;
                const scanData = progress.scan;

                if (syncData.status === 'running') {
                    syncProgressContainer.style.display = 'block';
                    syncProgressBar.value = syncData.current;
                    syncProgressBar.max = syncData.total || 100;
                    syncProgressText.textContent = `${syncData.message} (${syncData.current} / ${syncData.total || '?'})`;
                }

                if (syncData.status !== 'running' && lastSyncStatus === 'running') {
                    syncProgressContainer.style.display = 'none';
                    setStatus(syncData.message, syncData.status === 'complete' ? 'success' : 'error');
                    if(syncData.status === 'complete') {
                        view.dispatchEvent(new CustomEvent('datachanged', { bubbles: true }));
                    }
                }
                
                if (scanData.status === 'running') {
                    scanProgressContainer.style.display = 'block';
                    scanProgressBar.value = scanData.current;
                    scanProgressBar.max = scanData.total || 100;
                    scanProgressText.textContent = `${scanData.message} (${scanData.current} / ${scanData.total || '?'})`;
                }

                if (scanData.status !== 'running' && lastScanStatus === 'running') {
                    scanProgressContainer.style.display = 'none';
                    setStatus(scanData.message, scanData.status === 'complete' ? 'success' : 'error');
                    if(scanData.status === 'complete') {
                        view.dispatchEvent(new CustomEvent('datachanged', { bubbles: true }));
                    }
                }

                lastSyncStatus = syncData.status;
                lastScanStatus = scanData.status;

                if (syncData.status !== 'running' && scanData.status !== 'running') {
                    stopProgressPolling();
                    setButtonsDisabled(false);
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
        lastSyncStatus = 'idle';

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
        lastScanStatus = 'idle';

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