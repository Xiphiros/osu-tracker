import { getRecommendation } from '../services/api.js';
import { createBeatmapCard } from '../components/BeatmapCard.js';
import { getIntFromMods } from '../utils/mods.js';

export function createRecommenderView() {
    const view = document.createElement('div');
    view.id = 'recommender-view';
    view.className = 'view';

    const savedSr = localStorage.getItem('recommender_sr') || '5.5';
    const savedBpm = localStorage.getItem('recommender_bpm') || '200';

    view.innerHTML = `
        <h2>Training Recommender</h2>
        <div class="recommender-controls">
            <div class="mod-selection-container"></div>
            <div class="recommender-inputs-wrapper">
                <div class="control-group">
                    <label for="target-sr">Target Star Rating</label>
                    <input type="number" id="target-sr" value="${savedSr}" step="0.1" min="1">
                </div>
                <div class="control-group">
                    <label for="max-bpm">Target Max BPM</label>
                    <input type="number" id="max-bpm" value="${savedBpm}" step="5" min="60">
                    <span class="bpm-helper-text"></span>
                </div>
            </div>
            <button id="find-map-button">Find a map</button>
        </div>
        <div id="recommender-result">
            <p>Select your mods, set your target SR and max BPM, then click "Find a map".</p>
        </div>
        <div id="recommender-feedback" class="recommender-feedback">
            <button id="passed-button">Passed Goal</button>
            <button id="failed-button">Failed Goal</button>
            <button id="skip-button">Skip Map</button>
        </div>
    `;

    const findButton = view.querySelector('#find-map-button');
    const srInput = view.querySelector('#target-sr');
    const bpmInput = view.querySelector('#max-bpm');
    const bpmHelperText = view.querySelector('.bpm-helper-text');
    const resultContainer = view.querySelector('#recommender-result');
    const feedbackContainer = view.querySelector('#recommender-feedback');
    const passedButton = view.querySelector('#passed-button');
    const failedButton = view.querySelector('#failed-button');
    const skipButton = view.querySelector('#skip-button');
    const modContainer = view.querySelector('.mod-selection-container');
    const statusMessage = document.getElementById('status-message');

    const activeMods = new Set();
    const trainingMods = ['EZ', 'HD', 'HR', 'DT', 'HT', 'FL'];

    let rerollCount = 0;
    let lastSearchParams = null;
    let excludedBeatmapIds = [];
    const MAX_REROLLS = 3;

    const resetSession = () => {
        rerollCount = 0;
        excludedBeatmapIds = [];
        lastSearchParams = null;
        findButton.textContent = 'Find a map';
        findButton.disabled = false;
    };

    const updateBpmHelper = () => {
        const bpm = parseInt(bpmInput.value, 10);
        if (isNaN(bpm)) {
            bpmHelperText.textContent = '';
            return;
        }

        if (activeMods.has('DT')) {
            bpmHelperText.textContent = `(Original map BPM will be ~${Math.round(bpm / 1.5)})`;
        } else if (activeMods.has('HT')) {
            bpmHelperText.textContent = `(Original map BPM will be ~${Math.round(bpm / 0.75)})`;
        } else {
            bpmHelperText.textContent = '';
        }
    };

    trainingMods.forEach(mod => {
        const button = document.createElement('button');
        button.className = 'mod-button';
        button.textContent = mod;
        button.dataset.mod = mod;
        button.addEventListener('click', () => {
            const deactivate = (modToDeactivate) => {
                if (activeMods.has(modToDeactivate)) {
                    activeMods.delete(modToDeactivate);
                    modContainer.querySelector(`[data-mod="${modToDeactivate}"]`).classList.remove('active');
                }
            };

            if (!activeMods.has(mod)) {
                if (mod === 'DT') { deactivate('HR'); deactivate('HT'); }
                if (mod === 'HT') { deactivate('DT'); }
                if (mod === 'HR') { deactivate('DT'); deactivate('EZ'); }
                if (mod === 'EZ') { deactivate('HR'); }
                activeMods.add(mod);
                button.classList.add('active');
            } else {
                activeMods.delete(mod);
                button.classList.remove('active');
            }
            updateBpmHelper();
        });
        modContainer.appendChild(button);
    });

    srInput.addEventListener('change', () => localStorage.setItem('recommender_sr', srInput.value));
    bpmInput.addEventListener('change', () => localStorage.setItem('recommender_bpm', bpmInput.value));
    bpmInput.addEventListener('input', updateBpmHelper);
    
    updateBpmHelper();

    const resetView = () => {
        resultContainer.innerHTML = '<p>Set your target SR and max BPM, then click "Find a map".</p>';
        feedbackContainer.style.display = 'none';
        resetSession();
        statusMessage.textContent = 'Ready to find a map.';
    };

    findButton.addEventListener('click', async () => {
        const sr = parseFloat(srInput.value);
        const bpm = parseInt(bpmInput.value, 10);
        const mods = getIntFromMods(Array.from(activeMods));
        const currentSearchParams = JSON.stringify({ sr, bpm, mods });

        if (lastSearchParams === currentSearchParams) {
            rerollCount++;
        } else {
            resetSession();
            lastSearchParams = currentSearchParams;
        }

        if (rerollCount >= MAX_REROLLS) {
            statusMessage.textContent = `Max rerolls reached. Change parameters to search again.`;
            findButton.disabled = true;
            return;
        }

        if (isNaN(sr) || isNaN(bpm)) {
            statusMessage.textContent = "Please enter valid SR and BPM values.";
            return;
        }

        findButton.disabled = true;
        statusMessage.textContent = `Searching... (Reroll ${rerollCount + 1} of ${MAX_REROLLS})`;
        resultContainer.innerHTML = '<p>Searching...</p>';
        feedbackContainer.style.display = 'none';

        try {
            const beatmap = await getRecommendation(sr, bpm, mods, excludedBeatmapIds);
            if (beatmap) {
                excludedBeatmapIds.push(beatmap.md5_hash);
                const card = createBeatmapCard(beatmap);
                resultContainer.innerHTML = '';
                resultContainer.appendChild(card);
                feedbackContainer.style.display = 'flex';
                statusMessage.textContent = 'Map found! Play it and report your result.';
                findButton.textContent = `Reroll (${MAX_REROLLS - rerollCount - 1} left)`;
            } else {
                resultContainer.innerHTML = `<p>No new map found matching your criteria. Try adjusting the values.</p>`;
                statusMessage.textContent = 'No new map found.';
                findButton.textContent = 'Find a map'; // Allow changing params
                lastSearchParams = null; // Force reset on next click
            }
        } catch (error) {
            console.error(error);
            resultContainer.innerHTML = `<p class="error">${error.message}</p>`;
            statusMessage.textContent = 'Error finding map.';
        } finally {
            findButton.disabled = (rerollCount + 1 >= MAX_REROLLS);
        }
    });

    passedButton.addEventListener('click', () => {
        const currentSr = parseFloat(srInput.value);
        const newSr = (currentSr + 0.1).toFixed(1);
        srInput.value = newSr;
        localStorage.setItem('recommender_sr', newSr);
        statusMessage.textContent = `SR increased to ${srInput.value}!`;
        resetView();
    });

    const decrementSrAndReset = () => {
        const currentSr = parseFloat(srInput.value);
        const newSr = (currentSr - 0.1).toFixed(1);
        srInput.value = newSr;
        localStorage.setItem('recommender_sr', newSr);
        statusMessage.textContent = `SR decreased to ${srInput.value}. Try again.`;
        resetView();
    };

    failedButton.addEventListener('click', decrementSrAndReset);
    skipButton.addEventListener('click', decrementSrAndReset);

    return view;
}