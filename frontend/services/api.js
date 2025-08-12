const API_BASE_URL = '/api'; // Use a relative path

export const getReplays = async () => {
    const response = await fetch(`${API_BASE_URL}/replays`);
    if (!response.ok) {
        throw new Error('Failed to fetch replays. Is the backend server running?');
    }
    return response.json();
};

export const scanReplays = async () => {
    const response = await fetch(`${API_BASE_URL}/scan`, { method: 'POST' });
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to scan replays.');
    }
    return response.json();
};

export const getSongFileUrl = (folderName, fileName) => {
    if (!folderName || !fileName) return '';
    return `${API_BASE_URL}/songs/${encodeURIComponent(folderName)}/${encodeURIComponent(fileName)}`;
};