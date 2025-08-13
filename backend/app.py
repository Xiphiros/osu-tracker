import os
import sys
import logging
import threading
import webview
import json
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from dotenv import load_dotenv

import database
import parser

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
# The global BEATMAP_CACHE is no longer needed. Data is in the database.

@app.route('/api/beatmaps', methods=['GET'])
def get_beatmaps():
    """API endpoint to get all stored beatmap data."""
    beatmaps = database.get_all_beatmaps()
    return jsonify(beatmaps)

@app.route('/api/replays', methods=['GET'])
def get_replays():
    """API endpoint to get all stored replay data, enriched with beatmap details."""
    player_name = request.args.get('player_name')
    
    def get_rank(grade_val):
        ranks = {0:"SS", 1:"S", 2:"SS", 3:"S", 4:"A", 5:"B", 6:"C", 7:"D"}
        return ranks.get(grade_val, "N/A")

    # The database now returns fully enriched replays via the JOIN.
    all_replays = database.get_all_replays(player_name=player_name)
    
    # Post-process to add dynamic data not stored in the DB (like rank).
    # All file-system and heavy calculation logic has been removed for performance.
    for replay in all_replays:
        beatmap_info = replay.get('beatmap', {})
        
        # Safely parse grades from the JSON string stored in the database.
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

    return jsonify(all_replays)

@app.route('/api/players', methods=['GET'])
def get_players():
    players = database.get_unique_players()
    return jsonify(players)

@app.route('/api/players/<player_name>/stats', methods=['GET'])
def get_player_stats(player_name):
    """Calculates and returns key statistics for a given player."""
    replays = database.get_all_replays(player_name=player_name)
    if not replays:
        return jsonify({
            "total_pp": 0,
            "play_count": 0,
            "top_play_pp": 0
        })

    # Filter out plays without valid PP for this calculation
    pp_plays = [r for r in replays if r.get('pp') is not None and r.get('pp') > 0]
    
    # Sort plays by PP descending to calculate weighted total
    pp_plays.sort(key=lambda r: r['pp'], reverse=True)

    total_pp = 0
    for i, replay in enumerate(pp_plays):
        total_pp += replay['pp'] * (0.95 ** i)
        
    top_play_pp = pp_plays[0]['pp'] if pp_plays else 0

    stats = {
        "total_pp": round(total_pp, 2),
        "play_count": len(replays),
        "top_play_pp": round(top_play_pp, 2)
    }
    return jsonify(stats)

@app.route('/api/songs/<path:file_path>')
def serve_song_file(file_path):
    osu_folder = os.getenv('OSU_FOLDER')
    if not osu_folder:
        return jsonify({"error": "OSU_FOLDER path not set"}), 500
    songs_dir = os.path.join(osu_folder, 'Songs')
    return send_from_directory(songs_dir, file_path)

@app.route('/api/scan', methods=['POST'])
def scan_replays_folder_endpoint():
    osu_folder = os.getenv('OSU_FOLDER')
    if not osu_folder:
        return jsonify({"error": "OSU_FOLDER path not set in .env file"}), 500
    replays_path = os.path.join(osu_folder, 'Data', 'r')
    songs_path = os.path.join(osu_folder, 'Songs')
    if not os.path.isdir(replays_path):
        return jsonify({"error": f"Replays directory not found at: {replays_path}"}), 404
    try:
        # We no longer sync beatmaps automatically before a replay scan.
        # This is now a separate user-initiated action.
        all_beatmaps = {b['md5_hash']: b for b in database.get_all_beatmaps()}
        if not all_beatmaps:
            logging.warning("Beatmap database is empty. Replay data may be incomplete. Please run a beatmap sync.")

        replay_files = [f for f in os.listdir(replays_path) if f.endswith('.osr')]
        processed_count = 0
        for file_name in replay_files:
            file_path = os.path.join(replays_path, file_name)
            try:
                replay_data = parser.parse_replay_file(file_path)
                if not replay_data or not replay_data.get('replay_md5'): continue
                
                replay_data.update({'pp': None, 'stars': None, 'map_max_combo': None, 'bpm': None, 'bpm_min': None, 'bpm_max': None})
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
                processed_count += 1
            except Exception as e:
                logging.error(f"Could not process file {file_name}: {e}", exc_info=True)
        return jsonify({"status": "Scan complete", "replays_found": len(replay_files), "replays_processed": processed_count})
    except Exception as e:
        logging.error(f"An error occurred during scan: {str(e)}", exc_info=True)
        return jsonify({"error": f"An error occurred during scan: {str(e)}"}), 500

@app.route('/api/sync-beatmaps', methods=['POST'])
def sync_beatmaps_endpoint():
    """API endpoint to trigger a full beatmap database synchronization."""
    try:
        sync_local_beatmaps()
        return jsonify({"status": "Beatmap database synchronization complete."})
    except Exception as e:
        logging.error(f"An error occurred during beatmap sync: {str(e)}", exc_info=True)
        return jsonify({"error": f"An error occurred during sync: {str(e)}"}), 500
              
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_index(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

def sync_local_beatmaps():
    """Parses osu!.db and associated .osu files to sync the local database."""
    osu_folder = os.getenv('OSU_FOLDER')
    if not osu_folder:
        logging.warning("OSU_FOLDER not set. Cannot sync beatmap database.")
        raise ValueError("OSU_FOLDER environment variable is not set.")
    
    db_path = os.path.join(osu_folder, 'osu!.db')
    if not os.path.exists(db_path):
        logging.warning(f"osu!.db not found at {db_path}. Cannot sync beatmap database.")
        raise FileNotFoundError(f"osu!.db not found at {db_path}")

    songs_path = os.path.join(osu_folder, 'Songs')
    
    logging.info("Parsing beatmap data from osu!.db...")
    beatmap_data = parser.parse_osu_db(db_path)
    logging.info(f"Found {len(beatmap_data)} beatmaps. Parsing .osu files for details...")

    # Iterate through all beatmaps and parse their .osu files for more details
    for i, (md5, beatmap) in enumerate(beatmap_data.items()):
        if (i + 1) % 500 == 0:
            logging.info(f"Parsing progress: {i + 1}/{len(beatmap_data)} beatmaps...")
            
        if beatmap.get('folder_name') and beatmap.get('osu_file_name'):
            osu_file_path = os.path.join(songs_path, beatmap['folder_name'], beatmap['osu_file_name'])
            if os.path.exists(osu_file_path):
                try:
                    osu_details = parser.parse_osu_file(osu_file_path)
                    beatmap.update(osu_details) # Merge details into the main dict
                except Exception as e:
                    logging.warning(f"Could not parse .osu file {osu_file_path}: {e}")

    logging.info(f"Finished parsing .osu files. Syncing with application database...")
    database.add_or_update_beatmaps(beatmap_data)

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

    webview.create_window(
        'osu! Local Score Tracker',
        'http://127.0.0.1:5000',
        width=1280,
        height=800,
        resizable=True,
        min_size=(960, 600)
    )
    webview.start(debug=not IS_BUNDLED)