let currentlyPlaying = {
    audio: null,
    onEndCallback: null,
};

/**
 * Plays an audio file from a given URL. Ensures only one audio track plays at a time.
 * @param {string} audioUrl The URL of the audio file to play.
 * @param {function} onPlayCallback A function to call when playback starts.
 * @param {function} onEndCallback A function to call when playback stops (paused, ended, or replaced).
 */
export function playAudio(audioUrl, onPlayCallback, onEndCallback) {
    // If there's an existing audio, stop it and run its cleanup callback.
    if (currentlyPlaying.audio) {
        currentlyPlaying.audio.pause();
        if (currentlyPlaying.onEndCallback) {
            currentlyPlaying.onEndCallback();
        }
    }

    // If we're clicking the same song that was just paused, it means we want to stop it.
    // Clear the state and exit.
    if (currentlyPlaying.audio && currentlyPlaying.audio.src === audioUrl) {
        currentlyPlaying.audio = null;
        currentlyPlaying.onEndCallback = null;
        return;
    }

    const audio = new Audio(audioUrl);
    currentlyPlaying.audio = audio;
    currentlyPlaying.onEndCallback = onEndCallback;

    const endHandler = () => {
        // Only run the callback if this is still the currently active audio.
        if (currentlyPlaying.audio === audio) {
            onEndCallback();
        }
    };

    audio.addEventListener('play', onPlayCallback);
    audio.addEventListener('pause', endHandler);
    audio.addEventListener('ended', endHandler);
    
    audio.play().catch(err => {
        console.error("Audio playback failed:", err);
        // Clean up if playback fails to start
        if(currentlyPlaying.audio === audio) {
             currentlyPlaying.audio = null;
             currentlyPlaying.onEndCallback = null;
        }
        onEndCallback();
    });
}