import { getRecommendation } from '../services/api.js';
import { createBeatmapCard } from '../components/BeatmapCard.js';

export function createRecommenderView() {
    const view = document.createElement('div');
    view.id = 'recommender-view';
    view.className = 'view';

    // Load saved values from localStorage, with defaults
    const savedSr = localStorage.getItem('recommender_sr') || '5.5';
    const savedBpm = localStorage.getItem('recommender_bpm') || '200';

    view.innerHTML = `
        <h2>Training Recommender</h2>
        <div class="recommender-controls">
            <div class="control-group">
                <label for="target-sr">Target Star Rating</label>
                <input type="number" id="target-sr" value="${savedSr}" step="0.1" min="1">
            </div>
            <div class="control-group">
                <label for="max-bpm">Max BPM</label>
                <input type="number" id="max-bpm" value="${savedBpm}" step="5" min="60">
            </div>
            <button id="find-map-button">Find a map</button>
        </div>
        <div id="recommender-result">
            <p>Set your target SR and max BPM, then click "Find a map".</p>
        </div>
        <div id="recommender-feedback" class="recommender-feedback">
            <button id="passed-button">Passed Goal</button>
            <button id="failed-button">Failed Goal</button>
        </div>
    `;

    const findButton = view.querySelector('#find-map-button');
    const srInput = view.querySelector('#target-sr');
    const bpmInput = view.querySelector('#max-bpm');
    const resultContainer = view.querySelector('#recommender-result');
    const feedbackContainer = view.querySelector('#recommender-feedback');
    const passedButton = view.querySelector('#passed-button');
    const failedButton = view.querySelector('#failed-button');
    const statusMessage = document.getElementById('status-message');

    // --- Event Listeners to save values on change ---
    srInput.addEventListener('change', () => {
        localStorage.setItem('recommender_sr', srInput.value);
    });
    bpmInput.addEventListener('change', () => {
        localStorage.setItem('recommender_bpm', bpmInput.value);
    });
    // ---

    const resetView = () => {
        resultContainer.innerHTML = '<p>Set your target SR and max BPM, then click "Find a map".</p>';
        feedbackContainer.style.display = 'none';
        findButton.disabled = false;
        statusMessage.textContent = 'Ready to find a map.';
    };

    findButton.addEventListener('click', async () => {
        const sr = parseFloat(srInput.value);
        const bpm = parseInt(bpmInput.value, 10);

        if (isNaN(sr) || isNaN(bpm)) {
            statusMessage.textContent = "Please enter valid SR and BPM values.";
            return;
        }

        findButton.disabled = true;
        statusMessage.textContent = `Searching for a map between ${sr.toFixed(2)} and ${(sr + 0.1).toFixed(2)} stars, under ${bpm} BPM...`;
        resultContainer.innerHTML = '<p>Searching...</p>';
        feedbackContainer.style.display = 'none';

        try {
            const beatmap = await getRecommendation(sr, bpm);
            if (beatmap) {
                const card = createBeatmapCard(beatmap);
                resultContainer.innerHTML = '';
                resultContainer.appendChild(card);
                feedbackContainer.style.display = 'flex';
                statusMessage.textContent = 'Map found! Play it and report your result.';
            } else {
                resultContainer.innerHTML = `<p>No map found matching your criteria. Try adjusting the values.</p>`;
                statusMessage.textContent = 'No map found.';
                findButton.disabled = false;
            }
        } catch (error) {
            console.error(error);
            resultContainer.innerHTML = `<p class="error">${error.message}</p>`;
            statusMessage.textContent = 'Error finding map.';
            findButton.disabled = false;
        }
    });

    passedButton.addEventListener('click', () => {
        const currentSr = parseFloat(srInput.value);
        const newSr = (currentSr + 0.1).toFixed(1);
        srInput.value = newSr;
        localStorage.setItem('recommender_sr', newSr); // Save new value
        statusMessage.textContent = `SR increased to ${srInput.value}!`;
        resetView();
    });

    failedButton.addEventListener('click', () => {
        const currentSr = parseFloat(srInput.value);
        const newSr = (currentSr - 0.1).toFixed(1);
        srInput.value = newSr;
        localStorage.setItem('recommender_sr', newSr); // Save new value
        statusMessage.textContent = `SR decreased to ${srInput.value}.`;
        resetView();
    });


    return view;
}