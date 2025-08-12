import os
from flask import Flask, jsonify
from flask_cors import CORS # Import CORS
from dotenv import load_dotenv

import database
import parser

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app) # Enable CORS for all routes
BEATMAP_CACHE = {}

@app.route('/api/replays', methods=['GET'])
def get_replays():
    """API endpoint to get all stored replay data."""
    all_replays = database.get_all_replays()
    return jsonify(all_replays)

@app.route('/api/beatmap/<string:md5_hash>', methods=['GET'])
def get_beatmap_info(md5_hash):
    """API endpoint to get specific beatmap info from the cache."""
    beatmap_info = BEATMAP_CACHE.get(md5_hash)
    if beatmap_info:
        return jsonify(beatmap_info)
    return jsonify({"error": "Beatmap not found in cache"}), 404

@app.route('/api/scan', methods=['POST'])
def scan_replays_folder():
    """
    API endpoint to scan the osu! replays folder, parse new replays,
    and add them to the database.
    """
    osu_folder = os.getenv('OSU_FOLDER')
    if not osu_folder:
        return jsonify({"error": "OSU_FOLDER path not set in .env file"}), 500

    replays_path = os.path.join(osu_folder, 'Data', 'r')
    
    if not os.path.isdir(replays_path):
        return jsonify({"error": f"Replays directory not found at: {replays_path}"}), 404

    try:
        replay_files = [f for f in os.listdir(replays_path) if f.endswith('.osr')]
        scanned_count = len(replay_files)
        
        for file_name in replay_files:
            file_path = os.path.join(replays_path, file_name)
            try:
                replay_data = parser.parse_replay_file(file_path)
                # Ensure replay_data is not empty and has a hash
                if replay_data and replay_data.get('replay_md5'):
                    database.add_replay(replay_data)
            except Exception as e:
                # Log errors for individual file parsing but continue the scan
                print(f"Could not parse file {file_name}: {e}")
        
        return jsonify({
            "status": "Scan complete",
            "replays_found": scanned_count
        })

    except Exception as e:
        return jsonify({"error": f"An error occurred during scan: {str(e)}"}), 500

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
    # Ensure the database is initialized before starting the app
    database.init_db()
    # Load beatmap data into memory on startup
    load_beatmap_cache()
    # Run the Flask web server
    app.run(debug=True, port=5000)