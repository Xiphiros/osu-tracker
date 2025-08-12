import sqlite3

DATABASE_FILE = 'osu_tracker.db'

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    return conn

def init_db():
    """Initializes the database and creates the 'replays' table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Added mods_used field
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS replays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_mode INTEGER,
            game_version INTEGER,
            beatmap_md5 TEXT,
            player_name TEXT,
            replay_md5 TEXT UNIQUE,
            num_300s INTEGER,
            num_100s INTEGER,
            num_50s INTEGER,
            num_gekis INTEGER,
            num_katus INTEGER,
            num_misses INTEGER,
            total_score INTEGER,
            max_combo INTEGER,
            mods_used INTEGER,
            pp REAL,
            stars REAL,
            map_max_combo INTEGER,
            played_at TEXT,
            parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

def add_replay(replay_data):
    """Adds a new replay record to the database. Ignores duplicates based on replay_md5."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Using INSERT OR IGNORE to gracefully handle duplicate replays
    cursor.execute('''
        INSERT OR IGNORE INTO replays (
            game_mode, game_version, beatmap_md5, player_name, replay_md5,
            num_300s, num_100s, num_50s, num_gekis, num_katus, num_misses,
            total_score, max_combo, mods_used, pp, stars, map_max_combo, played_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        replay_data.get('game_mode'), replay_data.get('game_version'),
        replay_data.get('beatmap_md5'), replay_data.get('player_name'),
        replay_data.get('replay_md5'), replay_data.get('num_300s'),
        replay_data.get('num_100s'), replay_data.get('num_50s'),
        replay_data.get('num_gekis'), replay_data.get('num_katus'),
        replay_data.get('num_misses'), replay_data.get('total_score'),
        replay_data.get('max_combo'), replay_data.get('mods_used'),
        replay_data.get('pp'), replay_data.get('stars'),
        replay_data.get('map_max_combo'), replay_data.get('played_at')
    ))
    
    conn.commit()
    conn.close()
    
def get_all_replays(player_name=None):
    """Retrieves all replay records from the database, optionally filtering by player name."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM replays"
    params = []
    if player_name:
        query += " WHERE player_name = ?"
        params.append(player_name)
    
    # Order by date played, most recent first, which is a better user-facing default.
    query += " ORDER BY played_at DESC"
    
    cursor.execute(query, params)
    replays = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return replays

def get_unique_players():
    """Retrieves a list of unique player names from the replays table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT player_name FROM replays ORDER BY player_name")
    players = [row['player_name'] for row in cursor.fetchall()]
    conn.close()
    return players

def update_replay_pp(replay_md5, pp, stars, map_max_combo):
    """Updates the pp, stars, and map_max_combo for an existing replay record."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE replays SET pp = ?, stars = ?, map_max_combo = ? WHERE replay_md5 = ?",
        (pp, stars, map_max_combo, replay_md5)
    )
    conn.commit()
    conn.close()

if __name__ == '__main__':
    # This will run only when you execute `python backend/database.py` directly.
    # It sets up the database file and the table.
    init_db()