import os
import json
import logging
import threading
from flask import Blueprint, jsonify, send_from_directory, request
from dotenv import set_key, load_dotenv

import database
from tasks import TASK_PROGRESS, scan_replays_task, sync_local_beatmaps_task
from config import env_path

# Create a Blueprint for API routes
api_blueprint = Blueprint('api', __name__, url_prefix='/api')

def _add_rank_to_replay(replay):
    """
    Calculates and adds the rank to a replay dictionary in-place.
    For osu!standard, it calculates from score stats. For other modes, it uses the grade from osu!.db.
    """
    beatmap_info = replay.get('beatmap', {})
    game_mode = replay.get('game_mode')

    # --- Live Rank Calculation for osu!standard (mode 0) ---
    if game_mode == 0:
        n300 = replay.get('num_300s', 0)
        n100 = replay.get('num_100s', 0)
        n50 = replay.get('num_50s', 0)
        n_miss = replay.get('num_misses', 0)

        num_circles = beatmap_info.get('num_hitcircles')
        num_sliders = beatmap_info.get('num_sliders')
        num_spinners = beatmap_info.get('num_spinners')
        
        if num_circles is not None and num_sliders is not None and num_spinners is not None:
            total_objects = num_circles + num_sliders + num_spinners
            if total_objects > 0 and (n300 + n100 + n50 + n_miss) == total_objects:
                ratio_300 = n300 / total_objects
                ratio_50 = n50 / total_objects
                accuracy = (n300 * 300 + n100 * 100 + n50 * 50) / (total_objects * 300)

                if accuracy == 1.0: replay['rank'] = "SS"
                elif ratio_300 > 0.9 and ratio_50 < 0.01 and n_miss == 0: replay['rank'] = "S"
                elif (ratio_300 > 0.8 and n_miss == 0) or (ratio_300 > 0.9): replay['rank'] = "A"
                elif (ratio_300 > 0.7 and n_miss == 0) or (ratio_300 > 0.8): replay['rank'] = "B"
                elif ratio_300 > 0.6: replay['rank'] = "C"
                else: replay['rank'] = "D"
                return

    # --- Fallback to osu!.db grade for other modes or if live calc fails ---
    def get_rank_from_grade(grade_val):
        ranks = {0: "SS", 1: "S", 2: "SS", 3: "S", 4: "A", 5: "B", 6: "C", 7: "D"}
        return ranks.get(grade_val, "N/A")

    try:
        grades = json.loads(beatmap_info.get('grades', '{}'))
    except (json.JSONDecodeError, TypeError):
        grades = {}

    grade_val = -1
    if game_mode == 0: grade_val = grades.get('osu')
    elif game_mode == 1: grade_val = grades.get('taiko')
    elif game_mode == 2: grade_val = grades.get('ctb')
    elif game_mode == 3: grade_val = grades.get('mania')
    
    replay['rank'] = get_rank_from_grade(grade_val)

def _calculate_accuracy(replay):
    """Helper to calculate osu!standard accuracy from a replay dict."""
    if replay.get('game_mode') == 0:
        total_hits = replay.get('num_300s', 0) + replay.get('num_100s', 0) + replay.get('num_50s', 0) + replay.get('num_misses', 0)
        if total_hits == 0: return 0.0
        return ((replay.get('num_300s', 0) * 300 + replay.get('num_100s', 0) * 100 + replay.get('num_50s', 0) * 50) / (total_hits * 300)) * 100
    return 0.0

@api_blueprint.route('/beatmaps', methods=['GET'])
def get_beatmaps():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    search_term = request.args.get('search')
    return jsonify(database.get_all_beatmaps(page=page, limit=limit, search_term=search_term))

@api_blueprint.route('/replays', methods=['GET'])
def get_replays():
    player_name = request.args.get('player_name')
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    search_term = request.args.get('search')
    replays_data = database.get_all_replays(player_name=player_name, page=page, limit=limit, search_term=search_term)
    for replay in replays_data['replays']:
        _add_rank_to_replay(replay)
    return jsonify(replays_data)

@api_blueprint.route('/replays/latest', methods=['GET'])
def get_latest_replay():
    player_name = request.args.get('player_name')
    if not player_name:
        return jsonify({"error": "Missing 'player_name' parameter."}), 400
    replays_data = database.get_all_replays(player_name=player_name, page=1, limit=1)
    if replays_data and replays_data['replays']:
        latest_replay = replays_data['replays'][0]
        _add_rank_to_replay(latest_replay)
        return jsonify(latest_replay)
    return jsonify({"message": "No replays found for this player."}), 404

@api_blueprint.route('/players', methods=['GET'])
def get_players():
    return jsonify(database.get_unique_players())

@api_blueprint.route('/players/<player_name>/stats', methods=['GET'])
def get_player_stats(player_name):
    replays = database.get_all_replays(player_name=player_name, limit=100000)['replays']
    if not replays:
        return jsonify({"total_pp": 0, "play_count": 0, "top_play_pp": 0})
    pp_plays = sorted([r for r in replays if r.get('pp', 0) > 0], key=lambda r: r['pp'], reverse=True)
    total_pp = sum(r['pp'] * (0.95 ** i) for i, r in enumerate(pp_plays))
    top_play_pp = pp_plays[0]['pp'] if pp_plays else 0
    return jsonify({
        "total_pp": round(total_pp, 2),
        "play_count": len(replays),
        "top_play_pp": round(top_play_pp, 2)
    })

@api_blueprint.route('/players/<player_name>/suggest-sr', methods=['GET'])
def suggest_sr(player_name):
    mods = request.args.get('mods', 0, type=int)
    replays = database.get_all_replays(player_name=player_name, limit=100000)['replays']
    CORE_MOD_MASK = 2 | 8 | 16 | 64 | 256 | 1024 # EZ, HD, HR, DT, HT, FL
    mod_plays = []
    for r in replays:
        if r.get('stars') and r.get('game_mode') == 0:
            if (r.get('mods_used', 0) & CORE_MOD_MASK) == (mods & CORE_MOD_MASK):
                mod_plays.append(r)
    if not mod_plays:
        return jsonify({"message": "No plays found with this mod combination."}), 404
    recent_plays = mod_plays[:100]
    average_sr = sum(p['stars'] for p in recent_plays) / len(recent_plays)
    return jsonify({"suggested_sr": average_sr, "plays_considered": len(recent_plays)})

@api_blueprint.route('/recommend', methods=['GET'])
def get_recommendation():
    target_sr = request.args.get('sr', type=float)
    max_bpm = request.args.get('bpm', type=int)
    mods = request.args.get('mods', 0, type=int)
    focus = request.args.get('focus')
    excluded_ids = request.args.get('exclude', '').split(',') if request.args.get('exclude') else []
    
    if target_sr is None or max_bpm is None:
        return jsonify({"error": "Missing 'sr' or 'bpm' parameters."}), 400
        
    beatmap = database.get_recommendation(target_sr, max_bpm, mods, excluded_ids, focus)
    if beatmap:
        return jsonify(beatmap)
    return jsonify({"message": "No new map found. Try adjusting the values."}), 404

@api_blueprint.route('/songs/<path:file_path>')
def serve_song_file(file_path):
    osu_folder = os.getenv('OSU_FOLDER')
    if not osu_folder:
        return jsonify({"error": "OSU_FOLDER path not set"}), 500
    return send_from_directory(os.path.join(osu_folder, 'Songs'), file_path)

@api_blueprint.route('/config', methods=['GET'])
def get_config():
    return jsonify({
        "osu_folder": os.getenv("OSU_FOLDER", ""),
        "default_player": os.getenv("DEFAULT_PLAYER", "")
    })

@api_blueprint.route('/config', methods=['POST'])
def save_config():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request body"}), 400
    try:
        if 'osu_folder' in data: set_key(env_path, "OSU_FOLDER", data['osu_folder'])
        if 'default_player' in data: set_key(env_path, "DEFAULT_PLAYER", data['default_player'])
        load_dotenv(dotenv_path=env_path, override=True)
        return jsonify({"message": "Configuration saved successfully."})
    except Exception as e:
        logging.error(f"Failed to save configuration: {e}", exc_info=True)
        return jsonify({"error": "Failed to write to .env file."}), 500

@api_blueprint.route('/scan', methods=['POST'])
def scan_replays_folder_endpoint():
    if TASK_PROGRESS['scan']['status'] == 'running':
        return jsonify({"error": "Scan already in progress."}), 409
    thread = threading.Thread(target=scan_replays_task)
    thread.daemon = True
    thread.start()
    return jsonify({"status": "Scan process started."}), 202

@api_blueprint.route('/sync-beatmaps', methods=['POST'])
def sync_beatmaps_endpoint():
    if TASK_PROGRESS['sync']['status'] == 'running':
        return jsonify({"error": "Sync already in progress."}), 409
    thread = threading.Thread(target=sync_local_beatmaps_task)
    thread.daemon = True
    thread.start()
    return jsonify({"status": "Sync process started."}), 202

@api_blueprint.route('/progress-status', methods=['GET'])
def get_progress_status():
    return jsonify(TASK_PROGRESS)