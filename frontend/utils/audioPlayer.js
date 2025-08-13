let currentlyPlaying = {
    url: null,
    audio: null,
    onPlay: null,
    onEnd: null,
};

/**
 * Stops the currently playing audio and cleans up its state.
 * @param {boolean} [shouldTriggerEnd=true] - Whether to call the onEnd callback for the UI.
 */
function stopCurrent(shouldTriggerEnd = true) {
    if (currentlyPlaying.audio) {
        // Remove event listeners to prevent them from firing after we've manually stopped the audio.
        currentlyPlaying.audio.onplay = null;
        currentlyPlaying.audio.onpause = null;
        currentlyPlaying.audio.onended = null;
        
        currentlyPlaying.audio.pause();

        if (shouldTriggerEnd && currentlyPlaying.onEnd) {
            currentlyPlaying.onEnd();
        }
        // Reset the state completely.
        currentlyPlaying = { url: null, audio: null, onPlay: null, onEnd: null };
    }
}

/**
 * Manages audio playback for the application, ensuring only one track plays at a time.
 * @param {string} audioUrl - The URL of the song to play.
 * @param {function} onPlayCallback - Function to call when playback starts.
 * @param {function} onEndCallback - Function to call when playback stops or is paused.
 */
export function playAudio(audioUrl, onPlayCallback, onEndCallback) {
    const isSameSong = currentlyPlaying.url === audioUrl;

    if (isSameSong) {
        // If it's the same song, toggle between play and pause.
        if (currentlyPlaying.audio.paused) {
            currentlyPlaying.audio.play();
        } else {
            currentlyPlaying.audio.pause();
        }
    } else {
        // If it's a new song, stop the old one.
        stopCurrent(); 

        const audio = new Audio(audioUrl);
        // Store the new audio and its callbacks in our state.
        currentlyPlaying = { url: audioUrl, audio, onPlay: onPlayCallback, onEnd: onEndCallback };
        
        audio.onplay = () => {
            if (currentlyPlaying.url === audioUrl && currentlyPlaying.onPlay) {
                currentlyPlaying.onPlay();
            }
        };
        audio.onpause = () => {
             if (currentlyPlaying.url === audioUrl && currentlyPlaying.onEnd) {
                currentlyPlaying.onEnd();
            }
        };
        audio.onended = () => {
            // When a song finishes on its own, call the end callback and then fully clean up the state.
            if (currentlyPlaying.url === audioUrl) {
                if (currentlyPlaying.onEnd) currentlyPlaying.onEnd();
                stopCurrent(false); // Clean up without re-triggering the callback.
            }
        };
        
        audio.play().catch(err => {
            console.error("Audio playback failed:", err);
            stopCurrent(false); // Clean up on error.
        });
    }
}

/**
 * Public function to explicitly stop any playing audio.
 */
export function stopAudio() {
    stopCurrent();
}