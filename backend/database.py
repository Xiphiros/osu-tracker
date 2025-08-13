import sqlite3
import logging
import json
import os
from dotenv import load_dotenv
import rosu_pp_py

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
        
        # Migration for replays table
        cursor.execute("PRAGMA table_info(replays)")
        replay_columns = [row['name'] for row in cursor.fetchall()]
        
        if 'bpm_min' not in replay_columns:
            logging.info("Applying migration: Adding 'bpm_min' to 'replays' table.")
            cursor.execute("ALTER TABLE replays ADD COLUMN bpm_min REAL")
        if 'bpm_max' not in replay_columns:
            logging.info("Applying migration: Adding 'bpm_max' to 'replays' table.")
            cursor.execute("ALTER TABLE replays ADD COLUMN bpm_max REAL")

        # Migration for beatmaps table
        cursor.execute("PRAGMA table_info(beatmaps)")
        beatmap_columns = [row['name'] for row in cursor.fetchall()]
        
        if 'stars' not in beatmap_columns:
            logging.info("Applying migration: Adding 'stars' to 'beatmaps' table.")
            cursor.execute("ALTER TABLE beatmaps ADD COLUMN stars REAL")
        if 'game_mode' not in beatmap_columns:
            logging.info("Applying migration: Adding 'game_mode' to 'beatmaps' table.")
            cursor.execute("ALTER TABLE beatmaps ADD COLUMN game_mode INTEGER")
        
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
            game_mode INTEGER,
            last_played_date TEXT,
            num_hitcircles INTEGER,
            num_sliders INTEGER,
            num_spinners INTEGER,
            ar REAL,
            cs REAL,
            hp REAL,
            od REAL,
            stars REAL,
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

def get_all_replays(player_name=None, page=1, limit=50):
    """
    Retrieves a paginated list of replay records, enriched with beatmap data.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    base_query = """
        FROM replays r
        LEFT JOIN beatmaps b ON r.beatmap_md5 = b.md5_hash
    """
    count_query = "SELECT COUNT(r.id) " + base_query
    select_query = """
        SELECT
            r.*,
            b.artist, b.title, b.creator, b.difficulty, b.folder_name,
            b.osu_file_name, b.grades, b.last_played_date, b.num_hitcircles,
            b.num_sliders, b.num_spinners, b.ar, b.cs, b.hp, b.od,
            b.audio_file, b.background_file,
            COALESCE(r.bpm, b.bpm) as bpm,
            COALESCE(r.bpm_min, b.bpm_min) as bpm_min,
            COALESCE(r.bpm_max, b.bpm_max) as bpm_max
    """ + base_query

    params = []
    if player_name:
        where_clause = " WHERE r.player_name = ?"
        count_query += where_clause
        select_query += where_clause
        params.append(player_name)
    
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    select_query += " ORDER BY r.played_at DESC LIMIT ? OFFSET ?"
    offset = (page - 1) * limit
    params.extend([limit, offset])
    
    cursor.execute(select_query, params)

    replays = []
    for row in cursor.fetchall():
        replay_dict = dict(row)
        if row['artist'] is None:
            replay_dict['beatmap'] = {}
        else:
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
    return {"replays": replays, "total": total}

def get_unique_players():
    """Retrieves a list of unique player names from the replays table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT player_name FROM replays ORDER BY player_name")
    players = [row['player_name'] for row in cursor.fetchall()]
    conn.close()
    return players

def get_all_beatmaps(page=1, limit=50):
    """Retrieves a paginated list of beatmap records from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM beatmaps")
    total = cursor.fetchone()[0]

    offset = (page - 1) * limit
    cursor.execute("SELECT * FROM beatmaps ORDER BY artist, title LIMIT ? OFFSET ?", (limit, offset))
    beatmaps = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"beatmaps": beatmaps, "total": total}

def add_or_update_beatmaps(beatmaps_data):
    """
    Inserts or updates a batch of beatmaps in the database.
    This uses an 'upsert' mechanism to efficiently add new maps and 
    backfill details for existing ones.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    beatmap_tuples = []
    for md5, data in beatmaps_data.items():
        beatmap_tuples.append((
            md5, data.get('artist'), data.get('title'), data.get('creator'), 
            data.get('difficulty'), data.get('folder_name'), data.get('osu_file_name'),
            json.dumps(data.get('grades', {})), data.get('game_mode'), data.get('last_played_date'),
            data.get('num_hitcircles'), data.get('num_sliders'), data.get('num_spinners'),
            data.get('ar'), data.get('cs'), data.get('hp'), data.get('od'), data.get('stars'),
            data.get('bpm'), data.get('audio_file'), data.get('background_file'), 
            data.get('bpm_min'), data.get('bpm_max')
        ))

    # This "upsert" query will insert a new row if the md5_hash doesn't exist.
    # If it does exist (ON CONFLICT), it updates the record. COALESCE is used
    # to ensure we don't overwrite existing parsed data with a NULL value if
    # a subsequent parse of the .osu file fails for some reason.
    cursor.executemany('''
        INSERT INTO beatmaps (
            md5_hash, artist, title, creator, difficulty, folder_name, osu_file_name,
            grades, game_mode, last_played_date, num_hitcircles, num_sliders, num_spinners,
            ar, cs, hp, od, stars, bpm,
            audio_file, background_file, bpm_min, bpm_max
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(md5_hash) DO UPDATE SET
            artist=excluded.artist,
            title=excluded.title,
            creator=excluded.creator,
            difficulty=excluded.difficulty,
            folder_name=excluded.folder_name,
            osu_file_name=excluded.osu_file_name,
            grades=excluded.grades,
            game_mode=excluded.game_mode,
            last_played_date=excluded.last_played_date,
            num_hitcircles=excluded.num_hitcircles,
            num_sliders=excluded.num_sliders,
            num_spinners=excluded.num_spinners,
            ar=excluded.ar, cs=excluded.cs, hp=excluded.hp, od=excluded.od, 
            stars=COALESCE(beatmaps.stars, excluded.stars),
            bpm=excluded.bpm,
            audio_file=COALESCE(beatmaps.audio_file, excluded.audio_file),
            background_file=COALESCE(beatmaps.background_file, excluded.background_file),
            bpm_min=COALESCE(beatmaps.bpm_min, excluded.bpm_min),
            bpm_max=COALESCE(beatmaps.bpm_max, excluded.bpm_max)
    ''', beatmap_tuples)
    
    conn.commit()
    logging.info(f"Database sync complete. Processed {len(beatmap_tuples)} beatmaps. "
                 f"({cursor.rowcount} rows affected)")
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
    
def get_recommendation(target_sr, max_bpm, mods, excluded_ids=[]):
    """
    Finds a single, random osu! standard beatmap matching the criteria,
    calculating difficulty with mods on the fly.
    """
    load_dotenv()
    conn = get_db_connection()
    cursor = conn.cursor()

    mods_dt = (mods & 64) > 0 or (mods & 512) > 0
    mods_ht = (mods & 256) > 0
    mods_hr = (mods & 16) > 0
    mods_ez = (mods & 2) > 0

    base_query = "SELECT * FROM beatmaps WHERE game_mode = 0 AND stars IS NOT NULL AND bpm IS NOT NULL"
    params = []

    if mods_dt:
        base_query += " AND bpm <= ?"
        params.append(max_bpm / 1.5)
        base_query += " AND stars BETWEEN ? AND ?"
        params.extend([target_sr * 0.5, target_sr * 0.8])
    elif mods_ht:
        base_query += " AND bpm <= ?"
        params.append(max_bpm / 0.75)
        base_query += " AND stars BETWEEN ? AND ?"
        params.extend([target_sr, target_sr * 1.5])
    elif mods_hr:
        base_query += " AND bpm <= ?"
        params.append(max_bpm)
        base_query += " AND stars BETWEEN ? AND ?"
        params.extend([target_sr * 0.7, target_sr * 0.95])
    elif mods_ez:
        base_query += " AND bpm <= ?"
        params.append(max_bpm)
        base_query += " AND stars BETWEEN ? AND ?"
        params.extend([target_sr * 1.2, target_sr * 2.5])
    else:
        base_query += " AND bpm <= ?"
        params.append(max_bpm)
        base_query += " AND stars >= ? AND stars < ?"
        params.extend([target_sr, target_sr + 0.1])

    if excluded_ids:
        placeholders = ','.join('?' for _ in excluded_ids)
        base_query += f" AND md5_hash NOT IN ({placeholders})"
        params.extend(excluded_ids)

    base_query += " ORDER BY RANDOM() LIMIT 100"
    
    logging.debug(f"Recommendation query: {base_query} with params {params}")
    cursor.execute(base_query, params)
    candidates = cursor.fetchall()
    conn.close()

    if not candidates:
        logging.warning("No initial candidates found from database for recommendation.")
        return None

    osu_folder = os.getenv('OSU_FOLDER')
    if not osu_folder:
        logging.error("OSU_FOLDER not set, cannot find .osu files for recommendation.")
        return None
    songs_path = os.path.join(osu_folder, 'Songs')
    
    sr_upper_bound = target_sr + 0.1

    for row in candidates:
        beatmap = dict(row)
        if not beatmap.get('folder_name') or not beatmap.get('osu_file_name'): continue
        
        osu_file_path = os.path.join(songs_path, beatmap['folder_name'], beatmap['osu_file_name'])
        if not os.path.exists(osu_file_path): continue

        try:
            rosu_map = rosu_pp_py.Beatmap(path=osu_file_path)
            diff_calc = rosu_pp_py.Difficulty(mods=mods)
            diff_attrs = diff_calc.calculate(rosu_map)
            modded_stars = diff_attrs.stars
            
            attr_builder = rosu_pp_py.BeatmapAttributesBuilder(map=rosu_map, mods=mods)
            modded_map_attrs = attr_builder.build()
            clock_rate = modded_map_attrs.clock_rate
            modded_bpm = beatmap.get('bpm', 0) * clock_rate
            
            logging.debug(f"Checking candidate {beatmap['osu_file_name']}: Modded SR={modded_stars:.2f}, Modded BPM={modded_bpm:.2f}")

            if target_sr <= modded_stars < sr_upper_bound and modded_bpm <= max_bpm:
                beatmap['stars'] = round(modded_stars, 2)
                beatmap['bpm'] = round(modded_bpm)
                if beatmap.get('bpm_min'): beatmap['bpm_min'] = round(beatmap['bpm_min'] * clock_rate)
                if beatmap.get('bpm_max'): beatmap['bpm_max'] = round(beatmap['bpm_max'] * clock_rate)
                beatmap['ar'] = round(modded_map_attrs.ar, 2)
                beatmap['cs'] = round(modded_map_attrs.cs, 2)
                beatmap['hp'] = round(modded_map_attrs.hp, 2)
                beatmap['od'] = round(modded_map_attrs.od, 2)

                logging.info(f"Found recommendation: {beatmap['title']} with mods {mods}, final stats: {beatmap['stars']}*, {beatmap['bpm']}BPM")
                return beatmap
                
        except Exception as e:
            logging.error(f"Could not calculate difficulty for {osu_file_path} with mods {mods}: {e}", exc_info=False)
            continue
            
    logging.warning(f"No map found matching criteria after checking {len(candidates)} candidates.")
    return None

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