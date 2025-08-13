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
        
        # --- Migration for replays table ---
        cursor.execute("PRAGMA table_info(replays)")
        replay_columns = [row['name'] for row in cursor.fetchall()]
        if 'bpm_min' not in replay_columns:
            logging.info("Applying migration: Adding 'bpm_min' to 'replays' table.")
            cursor.execute("ALTER TABLE replays ADD COLUMN bpm_min REAL")
        if 'bpm_max' not in replay_columns:
            logging.info("Applying migration: Adding 'bpm_max' to 'replays' table.")
            cursor.execute("ALTER TABLE replays ADD COLUMN bpm_max REAL")
        if 'aim' not in replay_columns:
            logging.info("Applying migration: Adding 'aim' to 'replays' table.")
            cursor.execute("ALTER TABLE replays ADD COLUMN aim REAL")
        if 'speed' not in replay_columns:
            logging.info("Applying migration: Adding 'speed' to 'replays' table.")
            cursor.execute("ALTER TABLE replays ADD COLUMN speed REAL")
        if 'slider_factor' not in replay_columns:
            logging.info("Applying migration: Adding 'slider_factor' to 'replays' table.")
            cursor.execute("ALTER TABLE replays ADD COLUMN slider_factor REAL")

        # --- Migration for beatmaps table ---
        cursor.execute("PRAGMA table_info(beatmaps)")
        beatmap_columns = [row['name'] for row in cursor.fetchall()]
        if 'stars' not in beatmap_columns:
            logging.info("Applying migration: Adding 'stars' to 'beatmaps' table.")
            cursor.execute("ALTER TABLE beatmaps ADD COLUMN stars REAL")
        if 'game_mode' not in beatmap_columns:
            logging.info("Applying migration: Adding 'game_mode' to 'beatmaps' table.")
            cursor.execute("ALTER TABLE beatmaps ADD COLUMN game_mode INTEGER")

        # --- Migration for beatmap_mod_cache table ---
        cursor.execute("PRAGMA table_info(beatmap_mod_cache)")
        cache_columns = [row['name'] for row in cursor.fetchall()]
        if 'aim' not in cache_columns:
            logging.info("Applying migration: Adding 'aim' to 'beatmap_mod_cache' table.")
            cursor.execute("ALTER TABLE beatmap_mod_cache ADD COLUMN aim REAL")
        if 'speed' not in cache_columns:
            logging.info("Applying migration: Adding 'speed' to 'beatmap_mod_cache' table.")
            cursor.execute("ALTER TABLE beatmap_mod_cache ADD COLUMN speed REAL")
        if 'slider_factor' not in cache_columns:
            logging.info("Applying migration: Adding 'slider_factor' to 'beatmap_mod_cache' table.")
            cursor.execute("ALTER TABLE beatmap_mod_cache ADD COLUMN slider_factor REAL")
        
        conn.commit()

    conn = get_db_connection()
    cursor = conn.cursor()
    
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
            aim REAL,
            speed REAL,
            slider_factor REAL,
            map_max_combo INTEGER,
            bpm REAL,
            played_at TEXT,
            parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            bpm_min REAL,
            bpm_max REAL
        )
    ''')

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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS beatmap_mod_cache (
            md5_hash TEXT NOT NULL,
            mods INTEGER NOT NULL,
            stars REAL,
            ar REAL,
            od REAL,
            cs REAL,
            hp REAL,
            bpm REAL,
            aim REAL,
            speed REAL,
            slider_factor REAL,
            PRIMARY KEY (md5_hash, mods)
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
        'aim': replay_data.get('aim'),
        'speed': replay_data.get('speed'),
        'slider_factor': replay_data.get('slider_factor'),
        'map_max_combo': replay_data.get('map_max_combo'),
        'bpm': replay_data.get('bpm'),
        'bpm_min': replay_data.get('bpm_min'),
        'bpm_max': replay_data.get('bpm_max'),
        'played_at': replay_data.get('played_at')
    }

    cursor.execute('''
        INSERT INTO replays (
            game_mode, game_version, beatmap_md5, player_name, replay_md5,
            num_300s, num_100s, num_50s, num_gekis, num_katus, num_misses,
            total_score, max_combo, mods_used, pp, stars, aim, speed, slider_factor, map_max_combo, 
            bpm, bpm_min, bpm_max, played_at
        ) VALUES (
            :game_mode, :game_version, :beatmap_md5, :player_name, :replay_md5,
            :num_300s, :num_100s, :num_50s, :num_gekis, :num_katus, :num_misses,
            :total_score, :max_combo, :mods_used, :pp, :stars, :aim, :speed, :slider_factor, :map_max_combo, 
            :bpm, :bpm_min, :bpm_max, :played_at
        )
        ON CONFLICT(replay_md5) DO UPDATE SET
            pp = excluded.pp,
            stars = excluded.stars,
            aim = excluded.aim,
            speed = excluded.speed,
            slider_factor = excluded.slider_factor,
            map_max_combo = excluded.map_max_combo,
            bpm = excluded.bpm,
            bpm_min = excluded.bpm_min,
            bpm_max = excluded.bpm_max
        WHERE replays.pp IS NULL AND excluded.pp IS NOT NULL
    ''', params)
    
    conn.commit()
    conn.close()

def get_all_replays(player_name=None, page=1, limit=50, search_term=None):
    """
    Retrieves a paginated list of replay records, enriched with beatmap data.
    Can be filtered by player name and a text search term.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    base_query = " FROM replays r LEFT JOIN beatmaps b ON r.beatmap_md5 = b.md5_hash "
    where_clauses = []
    params = []

    if player_name:
        where_clauses.append("r.player_name = ?")
        params.append(player_name)

    if search_term:
        search_like = f"%{search_term}%"
        where_clauses.append("(b.title LIKE ? OR b.artist LIKE ? OR b.creator LIKE ?)")
        params.extend([search_like, search_like, search_like])

    where_sql = ""
    if where_clauses:
        where_sql = " WHERE " + " AND ".join(where_clauses)
    
    count_query = "SELECT COUNT(r.id) " + base_query + where_sql
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    select_query = """
        SELECT
            r.*, b.artist, b.title, b.creator, b.difficulty, b.folder_name,
            b.osu_file_name, b.grades, b.last_played_date, b.num_hitcircles,
            b.num_sliders, b.num_spinners, b.ar, b.cs, b.hp, b.od,
            b.audio_file, b.background_file,
            COALESCE(r.bpm, b.bpm) as bpm,
            COALESCE(r.bpm_min, b.bpm_min) as bpm_min,
            COALESCE(r.bpm_max, b.bpm_max) as bpm_max
    """ + base_query + where_sql + " ORDER BY r.played_at DESC LIMIT ? OFFSET ?"
    
    offset = (page - 1) * limit
    params.extend([limit, offset])
    
    cursor.execute(select_query, params)

    replays = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Enrich with beatmap object
    for replay in replays:
        replay['beatmap'] = {
            'artist': replay.get('artist'), 'title': replay.get('title'), 'creator': replay.get('creator'),
            'difficulty': replay.get('difficulty'), 'folder_name': replay.get('folder_name'),
            'osu_file_name': replay.get('osu_file_name'), 'grades': replay.get('grades'),
            'last_played_date': replay.get('last_played_date'), 'num_hitcircles': replay.get('num_hitcircles'),
            'num_sliders': replay.get('num_sliders'), 'num_spinners': replay.get('num_spinners'),
            'ar': replay.get('ar'), 'cs': replay.get('cs'), 'hp': replay.get('hp'), 'od': replay.get('od'),
            'bpm': replay.get('bpm'), 'audio_file': replay.get('audio_file'), 
            'background_file': replay.get('background_file'),
            'bpm_min': replay.get('bpm_min'), 'bpm_max': replay.get('bpm_max')
        }

    return {"replays": replays, "total": total}

def get_unique_players():
    """Retrieves a list of unique player names from the replays table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT player_name FROM replays ORDER BY player_name")
    players = [row['player_name'] for row in cursor.fetchall()]
    conn.close()
    return players

def get_all_beatmaps(page=1, limit=50, search_term=None):
    """
    Retrieves a paginated list of beatmap records from the database,
    optionally filtered by a search term.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    where_sql = ""
    params = []
    if search_term:
        search_like = f"%{search_term}%"
        where_sql = " WHERE title LIKE ? OR artist LIKE ? OR creator LIKE ? "
        params.extend([search_like, search_like, search_like])

    cursor.execute("SELECT COUNT(*) FROM beatmaps" + where_sql, params)
    total = cursor.fetchone()[0]

    query = "SELECT * FROM beatmaps " + where_sql + " ORDER BY artist, title LIMIT ? OFFSET ?"
    offset = (page - 1) * limit
    params.extend([limit, offset])

    cursor.execute(query, params)
    beatmaps = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"beatmaps": beatmaps, "total": total}

def add_or_update_beatmaps(beatmaps_data):
    """
    Inserts or updates a batch of beatmaps in the database.
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

def add_beatmap_mod_cache(cache_data):
    """Inserts or updates a batch of modded difficulty caches."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    params = [(
        d['md5_hash'], d['mods'], d['stars'], d['ar'], d['od'], 
        d['cs'], d['hp'], d['bpm'], d.get('aim'), d.get('speed'), d.get('slider_factor')
    ) for d in cache_data]

    cursor.executemany('''
        INSERT INTO beatmap_mod_cache (md5_hash, mods, stars, ar, od, cs, hp, bpm, aim, speed, slider_factor)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(md5_hash, mods) DO UPDATE SET
            stars=excluded.stars,
            ar=excluded.ar,
            od=excluded.od,
            cs=excluded.cs,
            hp=excluded.hp,
            bpm=excluded.bpm,
            aim=excluded.aim,
            speed=excluded.speed,
            slider_factor=excluded.slider_factor
    ''', params)
    
    conn.commit()
    logging.info(f"Saved {len(params)} entries to beatmap mod cache.")
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
    
def get_recommendation(target_sr, max_bpm, mods, excluded_ids=[], focus=None):
    """
    Finds a single, random osu! standard beatmap matching the criteria
    by using a pre-calculated cache of modded difficulties.
    """
    load_dotenv()
    conn = get_db_connection()
    cursor = conn.cursor()

    base_mod = 0
    if (mods & 64): base_mod = 64      # DoubleTime
    elif (mods & 256): base_mod = 256   # HalfTime
    elif (mods & 16): base_mod = 16     # HardRock
    elif (mods & 2): base_mod = 2       # Easy
    
    sr_lower_bound = target_sr
    sr_upper_bound = target_sr + 0.15

    if base_mod != 0:
        params = [base_mod, sr_lower_bound, sr_upper_bound, max_bpm]
        focus_clause = ""
        if focus == 'aim':
            focus_clause = " AND c.aim > c.speed "
        elif focus == 'speed':
            focus_clause = " AND c.speed > c.aim "
        elif focus == 'technical':
            focus_clause = " AND c.slider_factor > 1.3 "

        exclude_placeholders = '?' * len(excluded_ids)
        query = f"""
            SELECT b.*
            FROM beatmap_mod_cache c
            JOIN beatmaps b ON c.md5_hash = b.md5_hash
            WHERE c.mods = ?
              AND c.stars >= ? AND c.stars < ?
              AND c.bpm <= ?
              AND b.game_mode = 0
              {focus_clause}
              {f"AND b.md5_hash NOT IN ({','.join(exclude_placeholders)})" if excluded_ids else ""}
            ORDER BY RANDOM()
            LIMIT 1
        """
        params.extend(excluded_ids)
        logging.debug(f"Recommendation query (cached): {query} with params {params}")
        cursor.execute(query, params)
        row = cursor.fetchone()
    else:
        exclude_placeholders = '?' * len(excluded_ids)
        query = f"""
            SELECT * FROM beatmaps
            WHERE game_mode = 0
              AND stars >= ? AND stars < ?
              AND bpm <= ?
              {f"AND md5_hash NOT IN ({','.join(exclude_placeholders)})" if excluded_ids else ""}
            ORDER BY RANDOM()
            LIMIT 1
        """
        params = [sr_lower_bound, sr_upper_bound, max_bpm] + excluded_ids
        logging.debug(f"Recommendation query (NoMod): {query} with params {params}")
        cursor.execute(query, params)
        row = cursor.fetchone()

    conn.close()

    if not row:
        logging.warning("No map found matching criteria from database.")
        return None

    beatmap = dict(row)
    osu_folder = os.getenv('OSU_FOLDER')
    if not osu_folder:
        logging.error("OSU_FOLDER not set, cannot find .osu file for final calculation.")
        return beatmap

    songs_path = os.path.join(osu_folder, 'Songs')
    osu_file_path = os.path.join(songs_path, beatmap['folder_name'], beatmap['osu_file_name'])

    if not os.path.exists(osu_file_path):
        logging.warning(f"Could not find .osu file for recommended map: {osu_file_path}")
        return beatmap

    try:
        rosu_map = rosu_pp_py.Beatmap(path=osu_file_path)
        diff_calc = rosu_pp_py.Difficulty(mods=mods)
        diff_attrs = diff_calc.calculate(rosu_map)
        
        attr_builder = rosu_pp_py.BeatmapAttributesBuilder(map=rosu_map, mods=mods)
        modded_map_attrs = attr_builder.build()

        beatmap['stars'] = round(diff_attrs.stars, 2)
        beatmap['aim'] = round(diff_attrs.aim, 2)
        beatmap['speed'] = round(diff_attrs.speed, 2)
        beatmap['slider_factor'] = round(diff_attrs.slider_factor, 2)
        beatmap['bpm'] = round(beatmap['bpm'] * modded_map_attrs.clock_rate)
        beatmap['ar'] = round(modded_map_attrs.ar, 2)
        beatmap['cs'] = round(modded_map_attrs.cs, 2)
        beatmap['hp'] = round(modded_map_attrs.hp, 2)
        beatmap['od'] = round(modded_map_attrs.od, 2)
        
        logging.info(f"Found recommendation: {beatmap['title']} with mods {mods}, final stats: {beatmap['stars']}*, {beatmap['bpm']}BPM")
        return beatmap

    except Exception as e:
        logging.error(f"Could not perform final calculation for {osu_file_path} with mods {mods}: {e}", exc_info=False)
        return beatmap

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
    init_db()