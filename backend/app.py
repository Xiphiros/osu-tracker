import os
import logging
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

import database
import parser

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# Correctly configure Flask to serve all files from the frontend directory at the root URL
app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app) # Enable CORS for all routes
BEATMAP_CACHE = {}

@app.route('/api/replays', methods=['GET'])
def get_replays():
    """API endpoint to get all stored replay data, enriched with beatmap details."""
    osu_folder = os.getenv('OSU_FOLDER')
    if not osu_folder:
        return jsonify({"error": "OSU_FOLDER path not set"}), 500

    songs_path = os.path.join(osu_folder, 'Songs')
    
    # Helper function for grade mapping
    def get_rank(grade_val):
        # Based on osu! wiki, but simplified. 0/1 are for silver SS/S with mods.
        ranks = {0:"SS", 1:"S", 2:"SS", 3:"S", 4:"A", 5:"B", 6:"C", 7:"D"}
        return ranks.get(grade_val, "N/A")

    all_replays = database.get_all_replays()
    enriched_replays = []

    for replay in all_replays:
        beatmap_info = BEATMAP_CACHE.get(replay['beatmap_md5'])
        enriched_replay = dict(replay)

        if beatmap_info:
            enriched_replay['beatmap'] = beatmap_info
            
            # Determine rank based on game mode
            game_mode = enriched_replay.get('game_mode')
            grades = beatmap_info.get('grades', {})
            grade_val = -1
            if game_mode == 0: grade_val = grades.get('osu')
            elif game_mode == 1: grade_val = grades.get('taiko')
            elif game_mode == 2: grade_val = grades.get('ctb')
            elif game_mode == 3: grade_val = grades.get('mania')
            enriched_replay['rank'] = get_rank(grade_val)
            
            # Parse .osu file for more details
            osu_file_path = os.path.join(
                songs_path, 
                beatmap_info['folder_name'], 
                beatmap_info['osu_file_name']
            )

            # Lazy-calculate PP for older records that don't have it
            if enriched_replay.get('pp') is None and os.path.exists(osu_file_path):
                pp_info = parser.calculate_pp(osu_file_path, enriched_replay)
                if pp_info and pp_info.get('pp') is not None:
                    enriched_replay.update(pp_info)
                    database.update_replay_pp(
                        enriched_replay['replay_md5'],
                        pp_info['pp'],
                        pp_info['stars'],
                        pp_info['map_max_combo']
                    )

            if os.path.normpath(osu_file_path).startswith(os.path.normpath(songs_path)):
                osu_details = parser.parse_osu_file(osu_file_path)
                enriched_replay['beatmap'].update(osu_details)

        logging.debug(f"Enriched replay data for frontend: {enriched_replay}")
        enriched_replays.append(enriched_replay)

    return jsonify(enriched_replays)

@app.route('/api/players', methods=['GET'])
def get_players():
    """API endpoint to get a list of unique players."""
    players = database.get_unique_players()
    return jsonify(players)

# The /api/songs endpoint is now a sub-path of the main app
@app.route('/api/songs/<path:file_path>')
def serve_song_file(file_path):
    """API endpoint to serve static files from the osu! Songs directory."""
    osu_folder = os.getenv('OSU_FOLDER')
    if not osu_folder:
        return jsonify({"error": "OSU_FOLDER path not set"}), 500
    
    songs_dir = os.path.join(osu_folder, 'Songs')
    return send_from_directory(songs_dir, file_path)

@app.route('/api/scan', methods=['POST'])
def scan_replays_folder():
    """
    API endpoint to scan the osu! replays folder, parse new replays,
    calculate their PP, and add them to the database.
    """
    osu_folder = os.getenv('OSU_FOLDER')
    if not osu_folder:
        return jsonify({"error": "OSU_FOLDER path not set in .env file"}), 500

    replays_path = os.path.join(osu_folder, 'Data', 'r')
    songs_path = os.path.join(osu_folder, 'Songs')
    
    if not os.path.isdir(replays_path):
        return jsonify({"error": f"Replays directory not found at: {replays_path}"}), 404

    try:
        replay_files = [f for f in os.listdir(replays_path) if f.endswith('.osr')]
        scanned_count = len(replay_files)
        
        for file_name in replay_files:
            file_path = os.path.join(replays_path, file_name)
            try:
                replay_data = parser.parse_replay_file(file_path)
                if not replay_data or not replay_data.get('replay_md5'):
                    continue

                # Prepare for PP calculation
                replay_data['pp'] = None
                replay_data['stars'] = None

                beatmap_info = BEATMAP_CACHE.get(replay_data['beatmap_md5'])
                if beatmap_info:
                    osu_file_path = os.path.join(
                        songs_path,
                        beatmap_info['folder_name'],
                        beatmap_info['osu_file_name']
                    )
                    if os.path.exists(osu_file_path):
                        pp_info = parser.calculate_pp(osu_file_path, replay_data)
                        replay_data.update(pp_info)
                
                database.add_replay(replay_data)
            except Exception as e:
                print(f"Could not parse file {file_name}: {e}")
        
        return jsonify({
            "status": "Scan complete",
            "replays_found": scanned_count
        })

    except Exception as e:
        return jsonify({"error": f"An error occurred during scan: {str(e)}"}), 500
# This route now correctly serves index.html for the root path.
# Other static files (like main.js, main.css) are handled automatically
# by the static_folder and static_url_path config above.
@app.route('/')
def serve_index():
    """Serves the main index.html file from the frontend folder."""
    return send_from_directory(app.static_folder, 'index.html')

def load_beatmap_cache():
    """Loads beatmap data from osu!.db into memory."""
    global BEATMAP_CACHE
    osu_folder = os.getenv('OSU_FOLDER')
    if not osu_folder:
        print("Warning: OSU_FOLDER not set. Cannot load beatmap cache.")
        return
    
    db_path = os.path.join(osu_folder, 'osu!.db')
    if not os.path.exists(db_path):
        print(f"Warning: osu!.db not found at {db_path}. Cannot load beatmap cache.")
        return
        
    print("Loading beatmap cache from osu!.db... This may take a moment.")
    BEATMAP_CACHE = parser.parse_osu_db(db_path)
    print(f"Beatmap cache loaded with {len(BEATMAP_CACHE)} entries.")


if __name__ == '__main__':
    database.init_db()
    load_beatmap_cache()
    app.run(debug=True, port=5000)