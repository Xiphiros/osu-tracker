import os
import sys
import logging
import threading
import webview
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

@app.route('/api/replays', methods=['GET'])
def get_replays():
    """API endpoint to get all stored replay data, enriched with beatmap details."""
    player_name = request.args.get('player_name')
    osu_folder = os.getenv('OSU_FOLDER')
    if not osu_folder:
        return jsonify({"error": "OSU_FOLDER path not set"}), 500

    songs_path = os.path.join(osu_folder, 'Songs')
    
    def get_rank(grade_val):
        ranks = {0:"SS", 1:"S", 2:"SS", 3:"S", 4:"A", 5:"B", 6:"C", 7:"D"}
        return ranks.get(grade_val, "N/A")

    # The database now returns fully enriched replays.
    all_replays = database.get_all_replays(player_name=player_name)
    
    # Post-process to add dynamic data not stored in the DB (like rank)
    for replay in all_replays:
        beatmap_info = replay.get('beatmap')
        if not beatmap_info:
            replay['rank'] = "N/A"
            continue

        try:
            # Grades are stored as a string representation of a dict, e.g., "{'osu': 4}"
            grades = eval(beatmap_info.get('grades', '{}'))
        except:
            grades = {}

        game_mode = replay.get('game_mode')
        grade_val = -1
        if game_mode == 0: grade_val = grades.get('osu')
        elif game_mode == 1: grade_val = grades.get('taiko')
        elif game_mode == 2: grade_val = grades.get('ctb')
        elif game_mode == 3: grade_val = grades.get('mania')
        replay['rank'] = get_rank(grade_val)

        # This back-filling logic is still valuable for replays on maps that
        # might not be in the database yet, or for calculating PP on the fly.
        if beatmap_info and beatmap_info.get('folder_name'):
            osu_file_path = os.path.join(
                songs_path, beatmap_info['folder_name'], beatmap_info['osu_file_name']
            )

            if os.path.exists(osu_file_path):
                # Back-fill PP if it's missing from the replay record
                if replay.get('pp') is None:
                    pp_info = parser.calculate_pp(osu_file_path, replay)
                    if pp_info and pp_info.get('pp') is not None:
                        replay.update(pp_info)
                        database.update_replay_pp(
                            replay['replay_md5'], pp_info['pp'], pp_info['stars'], pp_info['map_max_combo']
                        )

                # Back-fill detailed BPM if it's missing
                if replay['beatmap'].get('bpm_min') is None:
                    osu_details = parser.parse_osu_file(osu_file_path)
                    if osu_details.get('bpm') is not None:
                        # Update the database for both the replay and the beatmap table
                        database.update_replay_bpm(
                            replay['replay_md5'],
                            osu_details.get('bpm'),
                            osu_details.get('bpm_min'),
                            osu_details.get('bpm_max')
                        )
                        # We don't have a specific beatmap update function for this yet,
                        # but this could be added in the future.
                        replay['beatmap'].update(osu_details)

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
def scan_replays_folder():
    osu_folder = os.getenv('OSU_FOLDER')
    if not osu_folder:
        return jsonify({"error": "OSU_FOLDER path not set in .env file"}), 500
    replays_path = os.path.join(osu_folder, 'Data', 'r')
    songs_path = os.path.join(osu_folder, 'Songs')
    if not os.path.isdir(replays_path):
        return jsonify({"error": f"Replays directory not found at: {replays_path}"}), 404
    try:
        logging.info("Syncing local beatmap database before scan...")
        sync_local_beatmaps()
        logging.info("Beatmap database sync complete.")

        all_replays = database.get_all_replays()
        existing_replays = {r['replay_md5']: r for r in all_replays}
        all_beatmaps = {b['md5_hash']: b for b in database.get_all_beatmaps()} # Assumes a get_all_beatmaps function

        replay_files = [f for f in os.listdir(replays_path) if f.endswith('.osr')]
        for file_name in replay_files:
            file_path = os.path.join(replays_path, file_name)
            try:
                replay_data = parser.parse_replay_file(file_path)
                if not replay_data or not replay_data.get('replay_md5'): continue
                
                # Skip if replay exists and has PP data
                existing = existing_replays.get(replay_data['replay_md5'])
                if existing and existing.get('pp') is not None:
                    continue

                # Initialize fields
                replay_data.update({'pp': None, 'stars': None, 'map_max_combo': None, 'bpm': None, 'bpm_min': None, 'bpm_max': None})
                beatmap_info = all_beatmaps.get(replay_data['beatmap_md5'])
                
                if beatmap_info:
                    osu_file_path = os.path.join(songs_path, beatmap_info['folder_name'], beatmap_info['osu_file_name'])
                    if os.path.exists(osu_file_path):
                        pp_info = parser.calculate_pp(osu_file_path, replay_data)
                        replay_data.update(pp_info)
                        
                        osu_details = parser.parse_osu_file(osu_file_path)
                        replay_data.update(osu_details)
                        
                database.add_replay(replay_data)
            except Exception as e:
                logging.error(f"Could not process file {file_name}: {e}", exc_info=True)
        return jsonify({"status": "Scan complete", "replays_found": len(replay_files)})
    except Exception as e:
        logging.error(f"An error occurred during scan: {str(e)}", exc_info=True)
        return jsonify({"error": f"An error occurred during scan: {str(e)}"}), 500
          
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_index(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

def sync_local_beatmaps():
    """Parses osu!.db and syncs the data with the local application database."""
    osu_folder = os.getenv('OSU_FOLDER')
    if not osu_folder:
        logging.warning("OSU_FOLDER not set. Cannot sync beatmap database.")
        return
    db_path = os.path.join(osu_folder, 'osu!.db')
    if not os.path.exists(db_path):
        logging.warning(f"osu!.db not found at {db_path}. Cannot sync beatmap database.")
        return
    logging.info("Parsing beatmap data from osu!.db...")
    beatmap_data = parser.parse_osu_db(db_path)
    logging.info(f"Found {len(beatmap_data)} beatmaps. Syncing with application database...")
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
    sync_local_beatmaps() # Sync on startup

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