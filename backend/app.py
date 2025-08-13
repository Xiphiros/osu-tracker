import os
import sys
import logging
import threading
import webview
import json
import signal
import concurrent.futures
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from dotenv import load_dotenv

import database
import parser
import rosu_pp_py

# Determine if running in a PyInstaller bundle
IS_BUNDLED = getattr(sys, 'frozen', False)

# Configure logging, use INFO for bundled app, DEBUG for dev
logging.basicConfig(
    level=logging.INFO if IS_BUNDLED else logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables from .env file.
load_dotenv()

# Set up static folder path.
if IS_BUNDLED:
    static_folder_path = os.path.join(sys._MEIPASS, 'frontend')
else:
    static_folder_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')

app = Flask(__name__, static_folder=static_folder_path, static_url_path='')
CORS(app)

# Global dictionary to track progress of background tasks.
# status can be 'idle', 'running', 'complete', 'error'
TASK_PROGRESS = {
    "sync": {"status": "idle", "current": 0, "total": 0, "message": ""},
    "scan": {"status": "idle", "current": 0, "total": 0, "message": ""}
}

@app.route('/api/beatmaps', methods=['GET'])
def get_beatmaps():
    """API endpoint to get a paginated list of stored beatmap data."""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    beatmaps_data = database.get_all_beatmaps(page=page, limit=limit)
    return jsonify(beatmaps_data)

@app.route('/api/replays', methods=['GET'])
def get_replays():
    """API endpoint to get a paginated list of stored replay data."""
    player_name = request.args.get('player_name')
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    
    def get_rank(grade_val):
        ranks = {0:"SS", 1:"S", 2:"SS", 3:"S", 4:"A", 5:"B", 6:"C", 7:"D"}
        return ranks.get(grade_val, "N/A")

    replays_data = database.get_all_replays(player_name=player_name, page=page, limit=limit)
    
    for replay in replays_data['replays']:
        beatmap_info = replay.get('beatmap', {})
        try:
            grades_str = beatmap_info.get('grades')
            grades = json.loads(grades_str) if grades_str else {}
        except (json.JSONDecodeError, TypeError):
            grades = {}

        game_mode = replay.get('game_mode')
        grade_val = -1
        if game_mode == 0: grade_val = grades.get('osu')
        elif game_mode == 1: grade_val = grades.get('taiko')
        elif game_mode == 2: grade_val = grades.get('ctb')
        elif game_mode == 3: grade_val = grades.get('mania')
        replay['rank'] = get_rank(grade_val)

    return jsonify(replays_data)

@app.route('/api/replays/latest', methods=['GET'])
def get_latest_replay():
    """API endpoint to get the single most recent replay for a player."""
    player_name = request.args.get('player_name')
    if not player_name:
        return jsonify({"error": "Missing 'player_name' parameter."}), 400
    
    # We can reuse get_all_replays since it sorts by date descending and supports limits.
    replays_data = database.get_all_replays(player_name=player_name, page=1, limit=1)
    
    if replays_data and replays_data['replays']:
        return jsonify(replays_data['replays'][0])
    else:
        return jsonify({"message": "No replays found for this player."}), 404

@app.route('/api/players', methods=['GET'])
def get_players():
    players = database.get_unique_players()
    return jsonify(players)

@app.route('/api/players/<player_name>/stats', methods=['GET'])
def get_player_stats(player_name):
    # Note: This still fetches all replays for stat calculation, which is correct.
    # We only paginate the display lists.
    replays = database.get_all_replays(player_name=player_name, limit=100000)['replays']
    if not replays:
        return jsonify({"total_pp": 0, "play_count": 0, "top_play_pp": 0})

    pp_plays = [r for r in replays if r.get('pp') is not None and r.get('pp') > 0]
    pp_plays.sort(key=lambda r: r['pp'], reverse=True)

    total_pp = sum(replay['pp'] * (0.95 ** i) for i, replay in enumerate(pp_plays))
    top_play_pp = pp_plays[0]['pp'] if pp_plays else 0

    stats = {
        "total_pp": round(total_pp, 2),
        "play_count": len(replays),
        "top_play_pp": round(top_play_pp, 2)
    }
    return jsonify(stats)

def _calculate_accuracy(replay):
    """Helper to calculate osu!standard accuracy from a replay dict."""
    if replay.get('game_mode') == 0:
        total_hits = replay.get('num_300s', 0) + replay.get('num_100s', 0) + replay.get('num_50s', 0) + replay.get('num_misses', 0)
        if total_hits == 0:
            return 0.0
        return ((replay.get('num_300s', 0) * 300 + replay.get('num_100s', 0) * 100 + replay.get('num_50s', 0) * 50) / (total_hits * 300)) * 100
    return 0.0

@app.route('/api/players/<player_name>/suggest-sr', methods=['GET'])
def suggest_sr(player_name):
    """Suggests a starting SR based on historical plays and goal criteria."""
    mods = request.args.get('mods', 0, type=int)
    min_acc = request.args.get('min_acc', type=float)
    min_score = request.args.get('min_score', type=int)
    max_misses = request.args.get('max_misses', type=int)
    
    replays = database.get_all_replays(player_name=player_name, limit=100000)['replays']
    
    valid_plays = []
    SCORE_V2_MOD = 536870912

    for r in replays:
        if r.get('stars') is None or r.get('game_mode') != 0:
            continue
            
        # Check if the play's mods are a superset of the required mods
        if (r.get('mods_used', 0) & mods) != mods:
            continue
            
        if min_acc is not None:
            if _calculate_accuracy(r) < min_acc:
                continue

        if min_score is not None:
            if (r.get('mods_used', 0) & SCORE_V2_MOD) == 0:
                continue 
            if r.get('total_score', 0) < min_score:
                continue
        
        if max_misses is not None:
            if r.get('num_misses', 0) > max_misses:
                continue
                
        valid_plays.append(r)
        
    if not valid_plays:
        return jsonify({"message": "No plays found matching your criteria."}), 404
        
    valid_plays.sort(key=lambda p: p['stars'], reverse=True)
    top_plays = valid_plays[:100]
    
    total_sr = sum(p['stars'] for p in top_plays)
    average_sr = total_sr / len(top_plays)
    
    return jsonify({"suggested_sr": average_sr, "plays_considered": len(top_plays)})

@app.route('/api/recommend', methods=['GET'])
def get_recommendation():
    """API endpoint to recommend a beatmap based on SR and BPM."""
    try:
        target_sr = request.args.get('sr', type=float)
        max_bpm = request.args.get('bpm', type=int)
        mods = request.args.get('mods', 0, type=int)
        exclude_str = request.args.get('exclude', '')
        excluded_ids = exclude_str.split(',') if exclude_str else []
        
        if target_sr is None or max_bpm is None:
            return jsonify({"error": "Missing 'sr' or 'bpm' parameters."}), 400

        beatmap = database.get_recommendation(target_sr, max_bpm, mods, excluded_ids)
        
        if beatmap:
            return jsonify(beatmap)
        else:
            return jsonify({"message": "No new map found. Try adjusting the values."}), 404
            
    except Exception as e:
        logging.error(f"Error in recommendation endpoint: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred."}), 500

@app.route('/api/songs/<path:file_path>')
def serve_song_file(file_path):
    osu_folder = os.getenv('OSU_FOLDER')
    if not osu_folder:
        return jsonify({"error": "OSU_FOLDER path not set"}), 500
    songs_dir = os.path.join(osu_folder, 'Songs')
    return send_from_directory(songs_dir, file_path)

@app.route('/api/scan', methods=['POST'])
def scan_replays_folder_endpoint():
    """Starts the replay scanning process in a background thread."""
    if TASK_PROGRESS['scan']['status'] == 'running':
        return jsonify({"error": "Scan already in progress."}), 409
    
    thread = threading.Thread(target=scan_replays_task)
    thread.daemon = True
    thread.start()
    return jsonify({"status": "Scan process started."}), 202

@app.route('/api/sync-beatmaps', methods=['POST'])
def sync_beatmaps_endpoint():
    """Starts the beatmap sync process in a background thread."""
    if TASK_PROGRESS['sync']['status'] == 'running':
        return jsonify({"error": "Sync already in progress."}), 409

    thread = threading.Thread(target=sync_local_beatmaps_task)
    thread.daemon = True
    thread.start()
    return jsonify({"status": "Sync process started."}), 202

@app.route('/api/progress-status', methods=['GET'])
def get_progress_status():
    """Endpoint for the frontend to poll for task progress."""
    return jsonify(TASK_PROGRESS)
              
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_index(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

def process_osu_file_and_cache(osu_file_path, base_bpm, md5):
    """Helper to process a .osu file and calculate difficulties for caching."""
    try:
        details = parser.parse_osu_file(osu_file_path)
        if details.get('bpm'): # Prefer .osu file BPM if available
            base_bpm = details['bpm']

        rosu_map = rosu_pp_py.Beatmap(path=osu_file_path)
        
        # Calculate NoMod difficulty
        nomod_diff_attrs = rosu_pp_py.Difficulty().calculate(rosu_map)
        details['stars'] = nomod_diff_attrs.stars
        
        # Calculate difficulties for cacheable mods
        # Mods that change SR/BPM: EZ (2), HR (16), DT (64), HT (256)
        mods_to_cache = [2, 16, 64, 256]
        mod_cache_results = []

        for mod_int in mods_to_cache:
            diff_calc = rosu_pp_py.Difficulty(mods=mod_int)
            diff_attrs = diff_calc.calculate(rosu_map)
            
            attr_builder = rosu_pp_py.BeatmapAttributesBuilder(map=rosu_map, mods=mod_int)
            map_attrs = attr_builder.build()

            mod_cache_results.append({
                'md5_hash': md5,
                'mods': mod_int,
                'stars': round(diff_attrs.stars, 2),
                'ar': round(map_attrs.ar, 2),
                'od': round(map_attrs.od, 2),
                'cs': round(map_attrs.cs, 2),
                'hp': round(map_attrs.hp, 2),
                'bpm': round(base_bpm * map_attrs.clock_rate, 2),
            })

        return md5, details, mod_cache_results
    except Exception as e:
        logging.warning(f"Could not parse/process file {osu_file_path}: {e}")
        return md5, {}, []

def sync_local_beatmaps_task():
    """Task to parse osu!.db, .osu files, and cache difficulties."""
    progress = TASK_PROGRESS['sync']
    progress['status'] = 'running'
    progress['current'] = 0
    progress['total'] = 0
    progress['message'] = 'Initializing...'
    
    try:
        osu_folder = os.getenv('OSU_FOLDER')
        if not osu_folder: raise ValueError("OSU_FOLDER environment variable is not set.")
        
        db_path = os.path.join(osu_folder, 'osu!.db')
        if not os.path.exists(db_path): raise FileNotFoundError(f"osu!.db not found at {db_path}")

        songs_path = os.path.join(osu_folder, 'Songs')
        
        progress['message'] = 'Parsing osu!.db...'
        beatmap_data = parser.parse_osu_db(db_path)
        
        tasks = []
        for md5, beatmap in beatmap_data.items():
             if beatmap.get('folder_name') and beatmap.get('osu_file_name') and beatmap.get('game_mode') == 0:
                osu_file_path = os.path.join(songs_path, beatmap['folder_name'], beatmap['osu_file_name'])
                if os.path.exists(osu_file_path):
                    tasks.append((osu_file_path, beatmap.get('bpm', 0), md5))

        progress['message'] = f"Calculating difficulty for {len(tasks)} beatmaps..."
        progress['total'] = len(tasks)
        progress['current'] = 0
        all_mod_caches = []

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_md5 = {executor.submit(process_osu_file_and_cache, path, bpm, md5): md5 for path, bpm, md5 in tasks}
            
            for future in concurrent.futures.as_completed(future_to_md5):
                progress['current'] += 1
                md5 = future_to_md5[future]
                beatmap_name = beatmap_data.get(md5, {}).get('osu_file_name', 'beatmap')
                progress['message'] = f"Processing {beatmap_name}..."
                
                try:
                    _md5, result_data, mod_caches = future.result()
                    if result_data:
                        beatmap_data[_md5].update(result_data)
                    if mod_caches:
                        all_mod_caches.extend(mod_caches)
                except Exception as e:
                    logging.error(f"Error processing future for {beatmap_name}: {e}", exc_info=True)

        progress['message'] = 'Saving beatmaps to database...'
        database.add_or_update_beatmaps(beatmap_data)
        
        if all_mod_caches:
            progress['message'] = f'Saving {len(all_mod_caches)} mod difficulty caches...'
            database.add_beatmap_mod_cache(all_mod_caches)

        progress['status'] = 'complete'
        progress['message'] = 'Beatmap database synchronization complete.'
    except Exception as e:
        logging.error(f"Error in sync task: {e}", exc_info=True)
        progress['status'] = 'error'
        progress['message'] = str(e)

def scan_replays_task():
    """Task to scan replay files, updating global progress."""
    progress = TASK_PROGRESS['scan']
    progress['status'] = 'running'
    progress['current'] = 0
    progress['total'] = 0
    progress['message'] = 'Initializing...'

    try:
        osu_folder = os.getenv('OSU_FOLDER')
        if not osu_folder: raise ValueError("OSU_FOLDER path not set in .env file")
        
        replays_path = os.path.join(osu_folder, 'Data', 'r')
        songs_path = os.path.join(osu_folder, 'Songs')
        if not os.path.isdir(replays_path): raise FileNotFoundError(f"Replays directory not found at: {replays_path}")

        all_beatmaps = {b['md5_hash']: b for b in database.get_all_beatmaps(limit=100000)['beatmaps']}
        if not all_beatmaps: logging.warning("Beatmap DB is empty. Replay data may be incomplete.")

        replay_files = [f for f in os.listdir(replays_path) if f.endswith('.osr')]
        progress['total'] = len(replay_files)

        for i, file_name in enumerate(replay_files):
            progress['current'] = i + 1
            progress['message'] = f'Scanning {file_name}...'
            
            file_path = os.path.join(replays_path, file_name)
            try:
                replay_data = parser.parse_replay_file(file_path)
                if not replay_data or not replay_data.get('replay_md5'): continue
                
                beatmap_info = all_beatmaps.get(replay_data['beatmap_md5'])
                if beatmap_info and beatmap_info.get('folder_name') and beatmap_info.get('osu_file_name'):
                    osu_file_path = os.path.join(songs_path, beatmap_info['folder_name'], beatmap_info['osu_file_name'])
                    if os.path.exists(osu_file_path):
                        pp_info = parser.calculate_pp(osu_file_path, replay_data)
                        replay_data.update(pp_info)
                        osu_details = parser.parse_osu_file(osu_file_path)
                        replay_data.update(osu_details)
                        database.update_beatmap_details(replay_data['beatmap_md5'], osu_details)
                
                database.add_replay(replay_data)
            except Exception as e:
                logging.error(f"Could not process file {file_name}: {e}", exc_info=True)
        
        progress['status'] = 'complete'
        progress['message'] = f"Scan complete. Processed {progress['total']} replays."
    except Exception as e:
        logging.error(f"Error in scan task: {e}", exc_info=True)
        progress['status'] = 'error'
        progress['message'] = str(e)


def run_server():
    """Runs the Flask server in a dedicated thread."""
    if IS_BUNDLED:
        from waitress import serve
        serve(app, host="127.0.0.1", port=5000)
    else:
        app.run(host="127.0.0.1", port=5000, debug=False)

if __name__ == '__main__':
    database.init_db()
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    logging.info("Backend server started in a background thread.")

    window = webview.create_window(
        'osu! Local Score Tracker',
        'http://127.0.0.1:5000',
        width=1280,
        height=800,
        resizable=True,
        min_size=(960, 600)
    )

    def on_closing():
        """
        Called when the pywebview window is closing. This function shuts down
        the Flask server gracefully when running in a development environment.
        """
        logging.info("Webview window is closing. Shutting down application.")
        # For the development server, send SIGINT to the process, like Ctrl+C.
        # This allows Werkzeug to shut down cleanly.
        if not IS_BUNDLED:
            os.kill(os.getpid(), signal.SIGINT)
        # For the bundled app, the daemon thread is terminated automatically.

    window.events.closing += on_closing

    webview.start(debug=not IS_BUNDLED)