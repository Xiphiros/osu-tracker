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
BEATMAP_CACHE = {}

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

    all_replays = database.get_all_replays(player_name=player_name)
    enriched_replays = []
    for replay in all_replays:
        beatmap_info = BEATMAP_CACHE.get(replay['beatmap_md5'])
        enriched_replay = dict(replay)
        
        if beatmap_info:
            enriched_replay['beatmap'] = beatmap_info.copy()

            if enriched_replay.get('bpm') is not None:
                enriched_replay['beatmap']['bpm'] = enriched_replay['bpm']
            if enriched_replay.get('bpm_min') is not None:
                enriched_replay['beatmap']['bpm_min'] = enriched_replay['bpm_min']
            if enriched_replay.get('bpm_max') is not None:
                enriched_replay['beatmap']['bpm_max'] = enriched_replay['bpm_max']

            game_mode = enriched_replay.get('game_mode')
            grades = beatmap_info.get('grades', {})
            grade_val = -1
            if game_mode == 0: grade_val = grades.get('osu')
            elif game_mode == 1: grade_val = grades.get('taiko')
            elif game_mode == 2: grade_val = grades.get('ctb')
            elif game_mode == 3: grade_val = grades.get('mania')
            enriched_replay['rank'] = get_rank(grade_val)
            
            osu_file_path = os.path.join(
                songs_path, beatmap_info['folder_name'], beatmap_info['osu_file_name']
            )

            if os.path.exists(osu_file_path):
                logging.debug(f"Processing replay for beatmap: {beatmap_info.get('osu_file_name')}")
                osu_details = parser.parse_osu_file(osu_file_path)
                logging.debug(f"Parsed .osu details: {osu_details}")

                if enriched_replay.get('pp') is None:
                    pp_info = parser.calculate_pp(osu_file_path, enriched_replay)
                    if pp_info and pp_info.get('pp') is not None:
                        enriched_replay.update(pp_info)
                        database.update_replay_pp(
                            enriched_replay['replay_md5'], pp_info['pp'], pp_info['stars'], pp_info['map_max_combo']
                        )

                if enriched_replay['beatmap'].get('bpm_min') is None and osu_details.get('bpm') is not None:
                    database.update_replay_bpm(
                        enriched_replay['replay_md5'],
                        osu_details.get('bpm'),
                        osu_details.get('bpm_min'),
                        osu_details.get('bpm_max')
                    )
                
                enriched_replay['beatmap'].update(osu_details)
                logging.debug(f"Final enriched beatmap object for response: {enriched_replay['beatmap']}")

        enriched_replays.append(enriched_replay)
    return jsonify(enriched_replays)

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
        logging.info("Refreshing beatmap cache before scan...")
        load_beatmap_cache()
        logging.info("Beatmap cache refreshed.")

        replay_files = [f for f in os.listdir(replays_path) if f.endswith('.osr')]
        for file_name in replay_files:
            file_path = os.path.join(replays_path, file_name)
            try:
                replay_data = parser.parse_replay_file(file_path)
                if not replay_data or not replay_data.get('replay_md5'): continue
                
                # Initialize fields
                replay_data.update({'pp': None, 'stars': None, 'map_max_combo': None, 'bpm': None, 'bpm_min': None, 'bpm_max': None})
                beatmap_info = BEATMAP_CACHE.get(replay_data['beatmap_md5'])
                
                if beatmap_info:
                    osu_file_path = os.path.join(songs_path, beatmap_info['folder_name'], beatmap_info['osu_file_name'])
                    if os.path.exists(osu_file_path):
                        # Enrich with PP and detailed BPM info before storing
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

def load_beatmap_cache():
    global BEATMAP_CACHE
    osu_folder = os.getenv('OSU_FOLDER')
    if not osu_folder:
        logging.warning("OSU_FOLDER not set. Cannot load beatmap cache.")
        return
    db_path = os.path.join(osu_folder, 'osu!.db')
    if not os.path.exists(db_path):
        logging.warning(f"osu!.db not found at {db_path}. Cannot load beatmap cache.")
        return
    logging.info("Loading beatmap cache from osu!.db...")
    BEATMAP_CACHE = parser.parse_osu_db(db_path)
    logging.info(f"Beatmap cache loaded with {len(BEATMAP_CACHE)} entries.")

def run_server():
    """Runs the Flask server in a dedicated thread."""
    if IS_BUNDLED:
        from waitress import serve
        serve(app, host="127.0.0.1", port=5000)
    else:
        app.run(host="127.0.0.1", port=5000, debug=False)

if __name__ == '__main__':
    database.init_db()
    load_beatmap_cache()

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