import {
	getRecommendation,
	getLatestReplay,
	scanReplays,
	getProgressStatus,
	getSuggestedSr
} from '../services/api.js';
import {
	createBeatmapCard
} from '../components/BeatmapCard.js';
import {
	createReplayCard
} from '../components/ReplayCard.js';
import {
	getIntFromMods,
	MODS
} from '../utils/mods.js';

let progressInterval = null;

// --- STATE MANAGEMENT ---
let sessionQueue = [];
let isSessionActive = false;
let currentStepIndex = -1;
let currentStepCompletedCount = 0;
let plannerActiveMods = new Set();
let rerollCount = 0;
let lastSearchParams = null;
let excludedBeatmapIds = [];
let currentRecommendation = null;
const MAX_REROLLS = 3;

function stopProgressPolling() {
	if (progressInterval) {
		clearInterval(progressInterval);
		progressInterval = null;
	}
}

function calculateAccuracy(replay) {
	const totalHits = replay.num_300s + replay.num_100s + replay.num_50s + replay.num_misses;
	if (totalHits === 0) return 0;
	return ((replay.num_300s * 300 + replay.num_100s * 100 + replay.num_50s * 50) / (totalHits * 300)) * 100;
}

export function createRecommenderView() {
	const view = document.createElement('div');
	view.id = 'recommender-view';
	view.className = 'view';

	const savedSr = localStorage.getItem('recommender_sr') || '5.5';
	const savedBpm = localStorage.getItem('recommender_bpm') || '200';
	const savedAcc = localStorage.getItem('goal_accuracy') || '96';
	const savedMisses = localStorage.getItem('goal_misses') || '';

	view.innerHTML = `
        <h2>Training Recommender</h2>

        <!-- PLANNER VIEW (default) -->
        <div id="recommender-planner">
            <div class="session-planner-controls">
                <h3>Add a Step to Your Plan</h3>
                <div class="planner-form-grid">
                    <div class="mod-selection-container"></div>
                    <div class="control-group">
                        <label for="planner-step-count">Maps to Pass</label>
                        <input type="number" id="planner-step-count" min="1" value="5">
                    </div>
                    <div class="control-group">
                        <label for="planner-goal-accuracy">Min Accuracy (%)</label>
                        <input type="number" id="planner-goal-accuracy" min="0" max="100" step="0.1" placeholder="e.g., 96" value="${savedAcc}">
                    </div>
                    <div class="control-group">
                        <label for="planner-goal-misses">Max Misses</label>
                        <input type="number" id="planner-goal-misses" min="0" step="1" placeholder="e.g., 5" value="${savedMisses}">
                    </div>
                    <div class="control-group" id="planner-goal-score-group" style="display: none;">
                        <label for="planner-goal-score">Min Score (SV2)</label>
                        <input type="number" id="planner-goal-score" min="0" step="1000" placeholder="e.g., 500k">
                    </div>
                    <div class="toggle-switch-container">
                        <label for="sv2-goal-toggle" class="toggle-switch-label">ScoreV2 Goal</label>
                        <label class="toggle-switch">
                            <input type="checkbox" id="sv2-goal-toggle">
                            <span class="slider round"></span>
                        </label>
                    </div>
                </div>
                <button id="add-step-button">Add Step to Plan</button>
            </div>

            <div class="session-plan-display">
                <h3>Session Plan</h3>
                <ul id="session-queue-list"></ul>
                <button id="start-session-button" disabled>Start Session</button>
            </div>
        </div>

        <!-- ACTIVE SESSION VIEW (hidden) -->
        <div id="recommender-active-session" style="display: none;">
            <div id="session-progress-display"></div>
            <div class="recommender-controls">
                 <div class="skill-focus-container">
                    <label>Skill Focus:</label>
                    <div class="radio-group">
                        <input type="radio" id="focus-balanced" name="skill-focus" value="balanced" checked>
                        <label for="focus-balanced">Balanced</label>
                        <input type="radio" id="focus-jumps" name="skill-focus" value="jumps">
                        <label for="focus-jumps">Jumps</label>
                        <input type="radio" id="focus-flow" name="skill-focus" value="flow">
                        <label for="focus-flow">Flow</label>
                        <input type="radio" id="focus-speed" name="skill-focus" value="speed">
                        <label for="focus-speed">Speed</label>
                        <input type="radio" id="focus-stamina" name="skill-focus" value="stamina">
                        <label for="focus-stamina">Stamina</label>
                    </div>
                </div>
                <div class="recommender-actions-wrapper">
                    <div class="control-group">
                        <label for="target-sr">Target Star Rating</label>
                        <div class="input-with-button">
                            <input type="number" id="target-sr" value="${savedSr}" step="0.1" min="1">
                            <button id="suggest-sr-button" class="small-button" title="Suggest SR based on your goals and play history">Suggest</button>
                        </div>
                    </div>
                    <div class="control-group">
                        <label for="max-bpm">Target Max BPM</label>
                        <input type="number" id="max-bpm" value="${savedBpm}" step="5" min="60">
                    </div>
                    <button id="find-map-button">Find a map</button>
                </div>
            </div>
        </div>

        <!-- SHARED ELEMENTS -->
        <div id="recommender-result"><p>Plan your session, then click "Start Session".</p></div>
        <div id="recommender-feedback" class="recommender-feedback">
            <div class="recommender-feedback-buttons">
                <button id="passed-button">Passed Goal</button>
                <button id="failed-button">Failed Goal</button>
                <button id="skip-button">Skip Map</button>
            </div>
            <button id="check-play-button">Check for New Play</button>
            <div class="progress-container" id="scan-progress-container">
                <progress id="scan-progress" class="progress-bar" value="0" max="100"></progress>
                <span id="scan-progress-text" class="progress-text"></span>
            </div>
            <div id="detection-result-container">
                <p id="detection-result-message"></p>
                <div id="detected-replay-card-container"></div>
                <button id="next-map-button">Find Next Map</button>
            </div>
        </div>
    `;

	const trainingMods = ['EZ', 'HD', 'HR', 'DT', 'HT', 'FL'];

	// --- Element Query Selectors ---
	const findButton = view.querySelector('#find-map-button');
	const srInput = view.querySelector('#target-sr');
	const suggestSrButton = view.querySelector('#suggest-sr-button');
	const bpmInput = view.querySelector('#max-bpm');
	const resultContainer = view.querySelector('#recommender-result');
	const feedbackContainer = view.querySelector('#recommender-feedback');
	const passedButton = view.querySelector('#passed-button');
	const failedButton = view.querySelector('#failed-button');
	const skipButton = view.querySelector('#skip-button');
	const checkPlayButton = view.querySelector('#check-play-button');
	const statusMessage = document.getElementById('status-message');
	const scanProgressContainer = view.querySelector('#scan-progress-container');
	const scanProgressBar = view.querySelector('#scan-progress');
	const scanProgressText = view.querySelector('#scan-progress-text');
	const detectionResultContainer = view.querySelector('#detection-result-container');
	const detectionResultMessage = view.querySelector('#detection-result-message');
	const detectedReplayCardContainer = view.querySelector('#detected-replay-card-container');
	const nextMapButton = view.querySelector('#next-map-button');

	// Planner UI
	const plannerView = view.querySelector('#recommender-planner');
	const plannerModContainer = view.querySelector('.planner-form-grid .mod-selection-container');
	const addStepButton = view.querySelector('#add-step-button');
	const sessionQueueList = view.querySelector('#session-queue-list');
	const startSessionButton = view.querySelector('#start-session-button');
	const sv2Toggle = view.querySelector('#sv2-goal-toggle');
	const plannerScoreGroup = view.querySelector('#planner-goal-score-group');

	// Active Session UI
	const activeSessionView = view.querySelector('#recommender-active-session');
	const sessionProgressDisplay = view.querySelector('#session-progress-display');


	// --- Functions ---
	const setFeedbackButtonsDisabled = (disabled) => {
		passedButton.disabled = disabled;
		failedButton.disabled = disabled;
		skipButton.disabled = disabled;
		checkPlayButton.disabled = disabled;
	};
    
    const renderQueue = () => {
        sessionQueueList.innerHTML = '';
        if (sessionQueue.length === 0) {
            sessionQueueList.innerHTML = '<p>No steps in your plan yet. Add one above!</p>';
            startSessionButton.disabled = true;
            return;
        }

        sessionQueue.forEach((step, index) => {
            const item = document.createElement('li');
            item.className = 'queue-item';
            if (isSessionActive && index === currentStepIndex) {
                item.classList.add('active-step');
            }

            let goalParts = [];
            if (step.goals.acc !== null) goalParts.push(`Acc: ${step.goals.acc}%`);
            if (step.goals.misses !== null) goalParts.push(`Misses: ≤${step.goals.misses}`);
            if (step.goals.useSv2 && step.goals.score !== null) goalParts.push(`Score: ≥${parseInt(step.goals.score).toLocaleString()}`);
            const goals = goalParts.join(' | ');

            item.innerHTML = `
                <div class="queue-item-details">
                    <div>
                        <span class="count">${step.count}x</span>
                        <span class="mods">${step.mods.length > 0 ? step.mods.join('') : 'NM'}</span> maps
                    </div>
                    <div class="queue-item-goals">${goals || 'No specific goals'}</div>
                </div>
                <button class="queue-item-remove" data-index="${index}">✖</button>
            `;
            sessionQueueList.appendChild(item);
        });

        sessionQueueList.querySelectorAll('.queue-item-remove').forEach(button => {
            button.addEventListener('click', (e) => {
                if (isSessionActive) return;
                const index = parseInt(e.currentTarget.dataset.index, 10);
                sessionQueue.splice(index, 1);
                renderQueue();
            });
        });
        startSessionButton.disabled = isSessionActive || sessionQueue.length === 0;
    };
    
    const addStepToQueue = () => {
        const count = parseInt(view.querySelector('#planner-step-count').value, 10);
        if (isNaN(count) || count < 1) {
            statusMessage.textContent = "Please enter a valid number of maps for the step.";
            return;
        }
        
        const accInput = view.querySelector('#planner-goal-accuracy');
        const missesInput = view.querySelector('#planner-goal-misses');
        const scoreInput = view.querySelector('#planner-goal-score');
        const useSv2 = sv2Toggle.checked;

        const acc = accInput.value ? parseFloat(accInput.value) : null;
        const missesValue = missesInput.value ? parseInt(missesInput.value, 10) : null;
        const misses = (missesValue !== null && !isNaN(missesValue)) ? missesValue : null;
        const score = useSv2 && scoreInput.value ? parseInt(scoreInput.value, 10) : null;

        if (acc === null && misses === null && score === null) {
            statusMessage.textContent = "Please define at least one goal (Accuracy, Misses, or Score).";
            return;
        }

        sessionQueue.push({
            count,
            mods: Array.from(plannerActiveMods),
            goals: { acc, misses, useSv2, score }
        });
        renderQueue();
    };

    const updateSessionProgressDisplay = () => {
        if (!isSessionActive) {
            sessionProgressDisplay.innerHTML = '';
            return;
        }
        const currentStep = sessionQueue[currentStepIndex];
        const modsText = currentStep.mods.length > 0 ? currentStep.mods.join('') : 'NM';
        sessionProgressDisplay.innerHTML = `
            <p id="session-progress-text">
                Step ${currentStepIndex + 1} of ${sessionQueue.length}: 
                <strong>(${currentStepCompletedCount}/${currentStep.count})</strong> ${modsText} maps
            </p>
            <button id="end-session-button">End Session</button>
        `;
        sessionProgressDisplay.querySelector('#end-session-button').addEventListener('click', endSession);
    };

    const loadStep = (stepIndex) => {
        currentStepIndex = stepIndex;
        currentStepCompletedCount = 0;
        updateSessionProgressDisplay();
        resetMapFinder();
        statusMessage.textContent = `New step started! Find a map to begin.`;
    };

    function startSession() {
        if (sessionQueue.length === 0) return;
        isSessionActive = true;
        plannerView.style.display = 'none';
        activeSessionView.style.display = 'block';
        loadStep(0);
    }
    
    function endSession() {
        isSessionActive = false;
        currentStepIndex = -1;
        currentStepCompletedCount = 0;
        sessionQueue = [];
        plannerView.style.display = 'block';
        activeSessionView.style.display = 'none';
        resultContainer.innerHTML = '<p>Session ended. Plan a new session to begin.</p>';
        feedbackContainer.style.display = 'none';
        renderQueue();
        statusMessage.textContent = "Session ended.";
    }

	const resetMapFinder = () => {
		rerollCount = 0;
		excludedBeatmapIds = [];
		lastSearchParams = null;
		currentRecommendation = null;
		findButton.textContent = 'Find a map';
		findButton.disabled = false;
        feedbackContainer.style.display = 'none';
		stopProgressPolling();
	};

	trainingMods.forEach(mod => {
		const button = document.createElement('button');
		button.className = 'mod-button';
		button.textContent = mod;
		button.dataset.mod = mod;
		button.addEventListener('click', () => {
			const deactivate = m => {
				if (plannerActiveMods.has(m)) {
					plannerActiveMods.delete(m);
					plannerModContainer.querySelector(`[data-mod="${m}"]`).classList.remove('active');
				}
			};
			if (!plannerActiveMods.has(mod)) {
				if (mod === 'DT') { deactivate('HT'); }
				if (mod === 'HT') deactivate('DT');
				if (mod === 'HR') deactivate('EZ');
				if (mod === 'EZ') deactivate('HR');
				plannerActiveMods.add(mod);
				button.classList.add('active');
			} else {
				plannerActiveMods.delete(mod);
				button.classList.remove('active');
			}
		});
		plannerModContainer.appendChild(button);
	});

	suggestSrButton.addEventListener('click', async () => {
        if (!isSessionActive) return;
		const playerName = document.getElementById('player-selector')?.value;
		if (!playerName) {
			statusMessage.textContent = 'Please select a player first.';
			return;
		}

        const currentStep = sessionQueue[currentStepIndex];
		const mods = getIntFromMods(currentStep.mods);
        const focus = view.querySelector('input[name="skill-focus"]:checked').value;
		const params = {
			mods,
            focus
		};

		suggestSrButton.disabled = true;
		suggestSrButton.textContent = '...';
		statusMessage.textContent = `Analyzing ${focus}-focused plays...`;

		try {
			const result = await getSuggestedSr(playerName, params);
			const suggestedSr = result.suggested_sr;
			srInput.value = suggestedSr.toFixed(1);
			localStorage.setItem('recommender_sr', srInput.value);
			statusMessage.textContent = `Suggestion based on your last ${result.plays_considered} ${focus}-focused plays: ${suggestedSr.toFixed(2)} ★`;
		} catch (error) {
			statusMessage.textContent = `Error: ${error.message}`;
		} finally {
			suggestSrButton.disabled = false;
			suggestSrButton.textContent = 'Suggest';
		}
	});

	srInput.addEventListener('change', () => localStorage.setItem('recommender_sr', srInput.value));
	bpmInput.addEventListener('change', () => localStorage.setItem('recommender_bpm', bpmInput.value));
    
    sv2Toggle.addEventListener('change', () => {
        plannerScoreGroup.style.display = sv2Toggle.checked ? 'flex' : 'none';
        if (!sv2Toggle.checked) {
            view.querySelector('#planner-goal-score').value = '';
        }
    });

	findButton.addEventListener('click', async () => {
        if (!isSessionActive) return;
        const currentStep = sessionQueue[currentStepIndex];

		const sr = parseFloat(srInput.value);
		const bpm = parseInt(bpmInput.value, 10);
		const mods = getIntFromMods(currentStep.mods);
        const focus = view.querySelector('input[name="skill-focus"]:checked').value;

		const currentSearchParams = JSON.stringify({ sr, bpm, mods, focus });

		if (lastSearchParams === currentSearchParams) rerollCount++;
		else {
            rerollCount = 0;
            excludedBeatmapIds = [];
        };
		lastSearchParams = currentSearchParams;

		if (rerollCount >= MAX_REROLLS) {
			statusMessage.textContent = `Max rerolls reached. Try different settings.`;
			findButton.disabled = true;
			return;
		}
		if (isNaN(sr) || isNaN(bpm)) {
			statusMessage.textContent = "Please enter valid SR and BPM values.";
			return;
		}
		findButton.disabled = true;
		statusMessage.textContent = `Searching for a ${focus}-focused map...`;
		resultContainer.innerHTML = '<p>Searching...</p>';
		feedbackContainer.style.display = 'none';
		try {
			const beatmap = await getRecommendation(sr, bpm, mods, excludedBeatmapIds, focus);
			if (beatmap) {
				excludedBeatmapIds.push(beatmap.md5_hash);
				currentRecommendation = {
					md5_hash: beatmap.md5_hash,
					mods: mods,
                    goals: { ...currentStep.goals } // Snapshot goals for this play
				};
				resultContainer.innerHTML = '';
				resultContainer.appendChild(createBeatmapCard(beatmap));
				feedbackContainer.style.display = 'flex';
				detectionResultContainer.style.display = 'none';
				statusMessage.textContent = 'Map found! Play it and report your result.';
				findButton.textContent = `Reroll (${MAX_REROLLS - rerollCount - 1} left)`;
			} else {
				resultContainer.innerHTML = `<p>No new map found. Try adjusting the values.</p>`;
				statusMessage.textContent = 'No new map found.';
				findButton.textContent = 'Find a map';
				lastSearchParams = null;
			}
		} catch (error) {
			resultContainer.innerHTML = `<p class="error">${error.message}</p>`;
			statusMessage.textContent = 'Error finding map.';
		} finally {
			findButton.disabled = (rerollCount + 1 >= MAX_REROLLS);
			setFeedbackButtonsDisabled(false);
		}
	});

    const handleSessionProgress = (passed, reason = "") => {
        const srChange = passed ? 0.1 : -0.1;
        const currentSr = parseFloat(srInput.value);
        const newSr = (currentSr + srChange).toFixed(1);
        srInput.value = newSr;
        localStorage.setItem('recommender_sr', newSr);
        
        currentStepCompletedCount++;

        updateSessionProgressDisplay();
        resetMapFinder();
        resultContainer.innerHTML = '<p>Ready for the next map!</p>';

        if (currentStepCompletedCount >= sessionQueue[currentStepIndex].count) {
            statusMessage.textContent = `Step complete! SR is now ${newSr}.`;
            currentStepIndex++;
            if (currentStepIndex >= sessionQueue.length) {
                endSession();
                statusMessage.textContent = `Session Complete! Congratulations!`;
                resultContainer.innerHTML = '<h2>Session Complete!</h2>';
            } else {
                loadStep(currentStepIndex);
            }
        } else {
            statusMessage.textContent = reason || `SR is now ${newSr}. Find the next map.`;
        }
    };

	passedButton.addEventListener('click', () => handleSessionProgress(true, "Goal Passed!"));
	failedButton.addEventListener('click', () => handleSessionProgress(false, "Goal Failed."));
	skipButton.addEventListener('click', () => handleSessionProgress(false, "Map skipped."));

	const pollScanProgress = (playerName) => {
		stopProgressPolling();
		progressInterval = setInterval(async () => {
			try {
				const progress = await getProgressStatus();
				if (progress.scan.status !== 'running') {
					stopProgressPolling();
					scanProgressContainer.style.display = 'none';
					if (progress.scan.status === 'complete') {
						statusMessage.textContent = 'Scan complete. Checking latest play...';
						const latestReplay = await getLatestReplay(playerName);
						if (latestReplay && latestReplay.beatmap_md5 === currentRecommendation.md5_hash) {
                            const coreRecMods = currentRecommendation.mods & (MODS.Easy | MODS.HardRock | MODS.DoubleTime | MODS.HalfTime);
                            const corePlayMods = latestReplay.mods_used & (MODS.Easy | MODS.HardRock | MODS.DoubleTime | MODS.HalfTime);

							if (corePlayMods === coreRecMods) {
                                const goals = currentRecommendation.goals;
								const playAcc = calculateAccuracy(latestReplay);
								const hasV2 = (latestReplay.mods_used & MODS.ScoreV2) > 0;
								let failReasons = [];

                                if (goals.acc !== null && playAcc < goals.acc) {
                                    failReasons.push(`Accuracy was ${playAcc.toFixed(2)}% (needed ${goals.acc}%)`);
                                }
                                if (goals.useSv2 && goals.score !== null) {
                                    if (!hasV2) {
                                        failReasons.push('Play was not on ScoreV2 (score goal requires V2)');
                                    } else if (latestReplay.total_score < goals.score) {
                                        failReasons.push(`Score was ${latestReplay.total_score.toLocaleString()} (needed ${goals.score.toLocaleString()})`);
                                    }
                                }
                                if (goals.misses !== null && latestReplay.num_misses > goals.misses) {
                                    failReasons.push(`Misses were ${latestReplay.num_misses} (max allowed ${goals.misses})`);
                                }
                                
                                const goalFailed = failReasons.length > 0;
								const resultMessage = goalFailed ? `Goal Failed: ${failReasons.join(', ')}` : 'Goal Passed!';
								detectionResultMessage.textContent = resultMessage;
								detectedReplayCardContainer.innerHTML = '';
								detectedReplayCardContainer.appendChild(createReplayCard(latestReplay));
								nextMapButton.onclick = () => handleSessionProgress(!goalFailed, failReasons.join(', ') || resultMessage);
								detectionResultContainer.style.display = 'flex';
                                statusMessage.textContent = `Play detected. Click below to continue.`;
							} else {
								statusMessage.textContent = `Play detected, but mods don't match.`;
								setFeedbackButtonsDisabled(false);
							}
						} else {
							statusMessage.textContent = 'No new play found for the recommended map.';
							setFeedbackButtonsDisabled(false);
						}
					} else {
						statusMessage.textContent = `Scan failed.`;
						setFeedbackButtonsDisabled(false);
					}
				} else {
					scanProgressBar.value = progress.scan.current;
					scanProgressBar.max = progress.scan.total || 100;
					scanProgressText.textContent = `${progress.scan.message} (${progress.scan.current}/${progress.scan.total || '?'})`;
				}
			} catch (e) {
				stopProgressPolling();
				scanProgressContainer.style.display = 'none';
				statusMessage.textContent = `Error: ${e.message}`;
				setFeedbackButtonsDisabled(false);
			}
		}, 500);
	};

	checkPlayButton.addEventListener('click', async () => {
		const playerName = document.getElementById('player-selector')?.value;
		if (!playerName) {
			statusMessage.textContent = 'Please select a player first.';
			return;
		}
		setFeedbackButtonsDisabled(true);
		scanProgressContainer.style.display = 'block';
		scanProgressBar.value = 0;
		scanProgressText.textContent = 'Starting scan...';
		try {
			await scanReplays();
			pollScanProgress(playerName);
		} catch (error) {
			statusMessage.textContent = `Error starting scan: ${error.message}`;
			setFeedbackButtonsDisabled(false);
			scanProgressContainer.style.display = 'none';
		}
	});
    
    // Wire up planner buttons
    addStepButton.addEventListener('click', addStepToQueue);
    startSessionButton.addEventListener('click', startSession);

    // Initial render
    renderQueue();
	return view;
}