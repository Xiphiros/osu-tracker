import { syncBeatmaps, scanReplays, getProgressStatus, getConfig, saveConfig, getPlayers, exportData, importData } from '../services/api.js';

let viewElement = null;
let isViewActive = false;

function handleProgressUpdate(progress) {
    if (!viewElement || !isViewActive) return;

    const syncProgressContainer = viewElement.querySelector('#sync-progress-container');
    const syncProgressBar = viewElement.querySelector('#sync-progress');
    const syncProgressText = viewElement.querySelector('#sync-progress-text');
    
    const scanProgressContainer = viewElement.querySelector('#scan-progress-container');
    const scanProgressBar = viewElement.querySelector('#scan-progress');
    const scanProgressText = viewElement.querySelector('#scan-progress-text');

    const syncData = progress.sync;
    const scanData = progress.scan;

    // Update Sync Progress UI
    if (syncData.status === 'running') {
        syncProgressContainer.style.display = 'block';
        syncProgressBar.value = syncData.current;
        syncProgressBar.max = syncData.total || 100;
        syncProgressText.textContent = syncData.message;
    } else {
        syncProgressContainer.style.display = 'none';
    }

    // Update Scan Progress UI
    if (scanData.status === 'running') {
        scanProgressContainer.style.display = 'block';
        scanProgressBar.value = scanData.current;
        scanProgressBar.max = scanData.total || 100;
        scanProgressText.textContent = scanData.message;
    } else {
        scanProgressContainer.style.display = 'none';
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
    viewElement = view;

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

        <div class="config-action-card">
            <h3>Data Management</h3>
            <p>Export your score database for backup, or import a database from another installation. Importing will replace your current data and requires an application restart.</p>
            <div class="data-actions">
                <button id="export-data-button">Export Data</button>
                <button id="import-data-button">Import Data</button>
            </div>
        </div>
    `;

    document.addEventListener('progressupdated', (e) => {
        handleProgressUpdate(e.detail);
        
        // Also update button states based on global progress
        const { sync, scan } = e.detail;
        const isTaskRunning = sync.status === 'running' || scan.status === 'running';
        view.querySelector('#sync-beatmaps-button').disabled = isTaskRunning;
        view.querySelector('#scan-replays-button-config').disabled = isTaskRunning;
        view.querySelector('#save-config-button').disabled = isTaskRunning;
    });

    view.addEventListener('viewactivated', async () => {
        isViewActive = true;
        loadConfigData(view);
        try {
            const progress = await getProgressStatus();
            handleProgressUpdate(progress);
        } catch(e) {
            console.error("Could not get initial progress for config view", e);
        }
    });
    
    view.addEventListener('viewdeactivated', () => {
        isViewActive = false;
    });
    
    const saveButton = view.querySelector('#save-config-button');
    const statusMessage = view.querySelector('#config-status-message');

    const setStatus = (message, type = 'info') => {
        statusMessage.textContent = message;
        statusMessage.style.display = 'block';
        statusMessage.className = type;
        
        // Hide info messages after a delay
        if (type === 'info') {
            setTimeout(() => {
                if (statusMessage.textContent === message) {
                    statusMessage.style.display = 'none';
                }
            }, 4000);
        }
    };

    saveButton.addEventListener('click', async () => {
        const osuFolder = view.querySelector('#osu-folder-input').value;
        const defaultPlayer = view.querySelector('#default-player-select').value;
        
        saveButton.disabled = true;
        saveButton.textContent = 'Saving...';
        statusMessage.style.display = 'none';

        try {
            await saveConfig({ "osu_folder": osuFolder, "default_player": defaultPlayer });
            setStatus('Settings saved successfully!', 'success');
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

    syncButton.addEventListener('click', async () => {
        statusMessage.style.display = 'none';
        try {
            await syncBeatmaps();
            view.dispatchEvent(new CustomEvent('taskstarted', { bubbles: true }));
        } catch (error) {
            setStatus(`Error starting sync: ${error.message}`, 'error');
        }
    });

    scanButton.addEventListener('click', async () => {
        statusMessage.style.display = 'none';
        try {
            await scanReplays();
            view.dispatchEvent(new CustomEvent('taskstarted', { bubbles: true }));
        } catch (error) {
            setStatus(`Error starting scan: ${error.message}`, 'error');
        }
    });

    const exportButton = view.querySelector('#export-data-button');
    const importButton = view.querySelector('#import-data-button');

    exportButton.addEventListener('click', async () => {
        setStatus('Opening export dialog...', 'info');
        try {
            const result = await exportData();
            setStatus(result.message, result.status);
        } catch (error) {
            setStatus(`Export failed: ${error.message}`, 'error');
        }
    });

    importButton.addEventListener('click', async () => {
        const allButtons = view.querySelectorAll('button');
        const allInputs = view.querySelectorAll('input, select');
        
        setStatus('Opening import dialog...', 'info');

        try {
            const result = await importData();
            setStatus(result.message, result.status);

            // If import was successful, disable controls to encourage a restart.
            if (result.status === 'success') {
                allButtons.forEach(b => b.disabled = true);
                allInputs.forEach(i => i.disabled = true);
            }
        } catch (error) {
            setStatus(`Import failed: ${error.message}`, 'error');
        }
    });

    return view;
}