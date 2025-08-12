import os
from flask import Flask, jsonify
from dotenv import load_dotenv

import database
import parser

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

@app.route('/api/replays', methods=['GET'])
def get_replays():
    """API endpoint to get all stored replay data."""
    all_replays = database.get_all_replays()
    return jsonify(all_replays)

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

if __name__ == '__main__':
    # Ensure the database is initialized before starting the app
    database.init_db()
    # Run the Flask web server
    app.run(debug=True, port=5000)