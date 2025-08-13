const API_BASE_URL = '/api'; // Use a relative path

export const getReplays = async (playerName = null, page = 1, limit = 50, searchTerm = null) => {
    let url = `${API_BASE_URL}/replays?page=${page}&limit=${limit}`;
    if (playerName) {
        url += `&player_name=${encodeURIComponent(playerName)}`;
    }
    if (searchTerm) {
        url += `&search=${encodeURIComponent(searchTerm)}`;
    }
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error('Failed to fetch replays. Is the backend server running?');
    }
    return response.json();
};

export const getLatestReplay = async (playerName) => {
    if (!playerName) throw new Error("Player name is required.");
    const response = await fetch(`${API_BASE_URL}/replays/latest?player_name=${encodeURIComponent(playerName)}`);
    if (response.status === 404) {
        return null;
    }
    if (!response.ok) {
        throw new Error('Failed to fetch latest replay.');
    }
    return response.json();
};

export const getPlayers = async () => {
    const response = await fetch(`${API_BASE_URL}/players`);
    if (!response.ok) {
        throw new Error('Failed to fetch players.');
    }
    return response.json();
};

export const getPlayerStats = async (playerName) => {
    const response = await fetch(`${API_BASE_URL}/players/${encodeURIComponent(playerName)}/stats`);
    if (!response.ok) {
        throw new Error('Failed to fetch player stats.');
    }
    return response.json();
};

export const scanReplays = async () => {
    const response = await fetch(`${API_BASE_URL}/scan`, { method: 'POST' });
    if (response.status !== 202 && !response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to start replay scan.');
    }
    return response.json();
};

export const syncBeatmaps = async () => {
    const response = await fetch(`${API_BASE_URL}/sync-beatmaps`, { method: 'POST' });
     if (response.status !== 202 && !response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to start beatmap sync.');
    }
    return response.json();
};

export const getProgressStatus = async () => {
    const response = await fetch(`${API_BASE_URL}/progress-status`);
    if (!response.ok) {
        throw new Error('Failed to fetch progress status.');
    }
    return response.json();
};

export const getSongFileUrl = (folderName, fileName) => {
    if (!folderName || !fileName) return '';
    return `${API_BASE_URL}/songs/${encodeURIComponent(folderName)}/${encodeURIComponent(fileName)}`;
};

export const getBeatmaps = async (page = 1, limit = 50, searchTerm = null) => {
    let url = `${API_BASE_URL}/beatmaps?page=${page}&limit=${limit}`;
    if (searchTerm) {
        url += `&search=${encodeURIComponent(searchTerm)}`;
    }
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error('Failed to fetch beatmaps.');
    }
    return response.json();
};

export const getRecommendation = async (sr, bpm, mods = 0, exclude = []) => {
    let url = `${API_BASE_URL}/recommend?sr=${sr}&bpm=${bpm}&mods=${mods}`;
    if (exclude.length > 0) {
        url += `&exclude=${exclude.join(',')}`;
    }
    const response = await fetch(url);
    if (response.status === 404) {
        return null; // This is an expected outcome if no map is found
    }
    if (!response.ok) {
        throw new Error('Failed to fetch recommendation.');
    }
    return response.json();
};

export const getSuggestedSr = async (playerName, params) => {
    let url = `${API_BASE_URL}/players/${encodeURIComponent(playerName)}/suggest-sr`;
    const searchParams = new URLSearchParams();

    // Filter out null/undefined/empty params before appending
    Object.keys(params).forEach(key => {
        if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
            searchParams.append(key, params[key]);
        }
    });

    const queryString = searchParams.toString();
    if (queryString) {
        url += `?${queryString}`;
    }

    const response = await fetch(url);
    if (response.status === 404) {
        const data = await response.json();
        throw new Error(data.message || 'No matching plays found.');
    }
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to fetch SR suggestion.');
    }
    return response.json();
};

export const getConfig = async () => {
    const response = await fetch(`${API_BASE_URL}/config`);
    if (!response.ok) {
        throw new Error('Failed to fetch configuration.');
    }
    return response.json();
};

export const saveConfig = async (configData) => {
    const response = await fetch(`${API_BASE_URL}/config`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(configData),
    });
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to save configuration.');
    }
    return response.json();
};