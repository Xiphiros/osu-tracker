import sqlite3
import logging
import json

DATABASE_FILE = 'osu_tracker.db'

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    return conn

def init_db():
    """Initializes the database, creates tables, and applies schema migrations."""
    
    def _migrate_db(conn):
        """Applies necessary schema migrations to an existing database."""
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(replays)")
        columns = [row['name'] for row in cursor.fetchall()]
        
        if 'bpm_min' not in columns:
            logging.info("Applying migration: Adding 'bpm_min' to 'replays' table.")
            cursor.execute("ALTER TABLE replays ADD COLUMN bpm_min REAL")
        if 'bpm_max' not in columns:
            logging.info("Applying migration: Adding 'bpm_max' to 'replays' table.")
            cursor.execute("ALTER TABLE replays ADD COLUMN bpm_max REAL")
        
        conn.commit()

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Updated table schema with detailed BPM fields
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
            bpm REAL,
            played_at TEXT,
            parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            bpm_min REAL,
            bpm_max REAL
        )
    ''')

    # New beatmaps table to store map details persistently.
    # md5_hash is the primary key as it's the natural unique identifier.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS beatmaps (
            md5_hash TEXT PRIMARY KEY,
            artist TEXT,
            title TEXT,
            creator TEXT,
            difficulty TEXT,
            folder_name TEXT,
            osu_file_name TEXT,
            grades TEXT,
            last_played_date TEXT,
            num_hitcircles INTEGER,
            num_sliders INTEGER,
            num_spinners INTEGER,
            ar REAL,
            cs REAL,
            hp REAL,
            od REAL,
            bpm REAL,
            audio_file TEXT,
            background_file TEXT,
            bpm_min REAL,
            bpm_max REAL
        )
    ''')
    
    conn.commit()
    _migrate_db(conn)
    conn.close()
    print("Database initialized and migrated successfully.")

def add_replay(replay_data):
    """Adds a new replay or updates it if calculated data was missing."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    params = {
        'game_mode': replay_data.get('game_mode'),
        'game_version': replay_data.get('game_version'),
        'beatmap_md5': replay_data.get('beatmap_md5'),
        'player_name': replay_data.get('player_name'),
        'replay_md5': replay_data.get('replay_md5'),
        'num_300s': replay_data.get('num_300s'),
        'num_100s': replay_data.get('num_100s'),
        'num_50s': replay_data.get('num_50s'),
        'num_gekis': replay_data.get('num_gekis'),
        'num_katus': replay_data.get('num_katus'),
        'num_misses': replay_data.get('num_misses'),
        'total_score': replay_data.get('total_score'),
        'max_combo': replay_data.get('max_combo'),
        'mods_used': replay_data.get('mods_used'),
        'pp': replay_data.get('pp'),
        'stars': replay_data.get('stars'),
        'map_max_combo': replay_data.get('map_max_combo'),
        'bpm': replay_data.get('bpm'),
        'bpm_min': replay_data.get('bpm_min'),
        'bpm_max': replay_data.get('bpm_max'),
        'played_at': replay_data.get('played_at')
    }

    # This query performs an "upsert".
    # If a replay with the same replay_md5 does not exist, it's inserted.
    # If it does exist (ON CONFLICT), it's updated, but only if the existing
    # replay is missing PP data and the new data has it. This efficiently
    # backfills data for old replays during a scan without overwriting
    # existing valid data.
    cursor.execute('''
        INSERT INTO replays (
            game_mode, game_version, beatmap_md5, player_name, replay_md5,
            num_300s, num_100s, num_50s, num_gekis, num_katus, num_misses,
            total_score, max_combo, mods_used, pp, stars, map_max_combo, 
            bpm, bpm_min, bpm_max, played_at
        ) VALUES (
            :game_mode, :game_version, :beatmap_md5, :player_name, :replay_md5,
            :num_300s, :num_100s, :num_50s, :num_gekis, :num_katus, :num_misses,
            :total_score, :max_combo, :mods_used, :pp, :stars, :map_max_combo, 
            :bpm, :bpm_min, :bpm_max, :played_at
        )
        ON CONFLICT(replay_md5) DO UPDATE SET
            pp = excluded.pp,
            stars = excluded.stars,
            map_max_combo = excluded.map_max_combo,
            bpm = excluded.bpm,
            bpm_min = excluded.bpm_min,
            bpm_max = excluded.bpm_max
        WHERE replays.pp IS NULL AND excluded.pp IS NOT NULL
    ''', params)
    
    conn.commit()
    conn.close()

def get_all_replays(player_name=None):
    """
    Retrieves all replay records, enriched with beatmap data using a JOIN.
    This is more efficient than merging in Python.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
        
    query = """
        SELECT
            r.*,
            b.artist, b.title, b.creator, b.difficulty, b.folder_name,
            b.osu_file_name, b.grades, b.last_played_date, b.num_hitcircles,
            b.num_sliders, b.num_spinners, b.ar, b.cs, b.hp, b.od,
            b.audio_file, b.background_file,
            COALESCE(r.bpm, b.bpm) as bpm,
            COALESCE(r.bpm_min, b.bpm_min) as bpm_min,
            COALESCE(r.bpm_max, b.bpm_max) as bpm_max
        FROM replays r
        LEFT JOIN beatmaps b ON r.beatmap_md5 = b.md5_hash
    """

    params = []
    if player_name:
        query += " WHERE r.player_name = ?"
        params.append(player_name)

    query += " ORDER BY r.played_at DESC"

    cursor.execute(query, params)

    replays = []
    for row in cursor.fetchall():
        replay_dict = dict(row)
        
        # If artist is None, the LEFT JOIN found no matching beatmap.
        # In this case, we create an empty beatmap object.
        if row['artist'] is None:
            replay_dict['beatmap'] = {}
        else:
            # Otherwise, we construct the nested beatmap object as expected by the frontend.
            replay_dict['beatmap'] = {
                'artist': row['artist'], 'title': row['title'], 'creator': row['creator'],
                'difficulty': row['difficulty'], 'folder_name': row['folder_name'],
                'osu_file_name': row['osu_file_name'], 'grades': row['grades'],
                'last_played_date': row['last_played_date'], 'num_hitcircles': row['num_hitcircles'],
                'num_sliders': row['num_sliders'], 'num_spinners': row['num_spinners'],
                'ar': row['ar'], 'cs': row['cs'], 'hp': row['hp'], 'od': row['od'],
                'bpm': row['bpm'], 'audio_file': row['audio_file'], 
                'background_file': row['background_file'],
                'bpm_min': row['bpm_min'], 'bpm_max': row['bpm_max']
            }
        replays.append(replay_dict)
        
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

def get_all_beatmaps():
    """Retrieves all beatmap records from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM beatmaps")
    beatmaps = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return beatmaps

def add_or_update_beatmaps(beatmaps_data):
    """
    Inserts or updates a batch of beatmaps in the database.
    This uses an 'upsert' mechanism to be efficient.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    beatmap_tuples = []
    for md5, data in beatmaps_data.items():
        beatmap_tuples.append((
            md5, data.get('artist'), data.get('title'), data.get('creator'), 
            data.get('difficulty'), data.get('folder_name'), data.get('osu_file_name'),
            json.dumps(data.get('grades', {})), data.get('last_played_date'),
            data.get('num_hitcircles'), data.get('num_sliders'), data.get('num_spinners'),
            data.get('ar'), data.get('cs'), data.get('hp'), data.get('od'), data.get('bpm')
        ))

    # Using INSERT OR IGNORE as we only want to add new maps from osu!.db
    # We don't want to overwrite potentially richer data from an API in the future.
    cursor.executemany('''
        INSERT OR IGNORE INTO beatmaps (
            md5_hash, artist, title, creator, difficulty, folder_name, osu_file_name,
            grades, last_played_date, num_hitcircles, num_sliders, num_spinners,
            ar, cs, hp, od, bpm
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', beatmap_tuples)
    
    conn.commit()
    logging.info(f"Database sync complete. Processed {len(beatmap_tuples)} beatmaps. "
                 f"({cursor.rowcount} new entries added)")
    conn.close()

def update_beatmap_details(md5_hash, details):
    """Updates a beatmap record with details parsed from the .osu file."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Only update if the details are not already present, to avoid unnecessary writes.
    cursor.execute('''
        UPDATE beatmaps 
        SET 
            audio_file = COALESCE(audio_file, ?),
            background_file = COALESCE(background_file, ?),
            bpm_min = COALESCE(bpm_min, ?),
            bpm_max = COALESCE(bpm_max, ?)
        WHERE md5_hash = ?
    ''', (
        details.get('audio_file'),
        details.get('background_file'),
        details.get('bpm_min'),
        details.get('bpm_max'),
        md5_hash
    ))
    
    conn.commit()
    conn.close()
    
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

def update_replay_bpm(replay_md5, bpm, bpm_min, bpm_max):
    """Updates the detailed BPM info for an existing replay record."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE replays SET bpm = ?, bpm_min = ?, bpm_max = ? WHERE replay_md5 = ?",
        (bpm, bpm_min, bpm_max, replay_md5)
    )
    conn.commit()
    conn.close()

if __name__ == '__main__':
    # This will run only when you execute `python backend/database.py` directly.
    # It sets up the database file and the table.
    init_db()