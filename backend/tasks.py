import os
import logging
import concurrent.futures
from flask import jsonify

import database
import parser
import rosu_pp_py

# Global dictionary to track progress of background tasks.
# status can be 'idle', 'running', 'complete', 'error'
TASK_PROGRESS = {
    "sync": {"status": "idle", "current": 0, "total": 0, "message": "", "batches_done": 0},
    "scan": {"status": "idle", "current": 0, "total": 0, "message": ""}
}

def process_osu_file_and_cache(osu_file_path, base_bpm, md5):
    """Helper function to parse a .osu file and pre-calculate modded difficulties."""
    try:
        # Get file-based details like audio/bg filenames and detailed BPM
        details = parser.parse_osu_file(osu_file_path)
        if details.get('bpm'):
            base_bpm = details['bpm']

        # Get NoMod difficulty attributes
        nomod_attrs = parser.calculate_difficulty(osu_file_path, mods=0)
        details.update(nomod_attrs)
        
        # Pre-calculate difficulty for common mod combinations
        mods_to_cache = [2, 16, 64, 256] # EZ, HR, DT, HT
        mod_cache_results = []

        rosu_map = rosu_pp_py.Beatmap(path=osu_file_path)

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
                'aim': round(diff_attrs.aim, 2) if diff_attrs.aim else None,
                'speed': round(diff_attrs.speed, 2) if diff_attrs.speed else None,
                'slider_factor': round(diff_attrs.slider_factor, 2) if diff_attrs.slider_factor else None,
                'speed_note_count': round(diff_attrs.speed_note_count, 2) if diff_attrs.speed_note_count else None,
                'aim_difficult_strain_count': round(diff_attrs.aim_difficult_strain_count, 2) if diff_attrs.aim_difficult_strain_count else None,
                'speed_difficult_strain_count': round(diff_attrs.speed_difficult_strain_count, 2) if diff_attrs.speed_difficult_strain_count else None,
                'aim_difficult_slider_count': round(diff_attrs.aim_difficult_slider_count, 2) if diff_attrs.aim_difficult_slider_count else None,
            })

        return md5, details, mod_cache_results
    except Exception as e:
        logging.warning(f"Could not parse/process file {osu_file_path}: {e}")
        return md5, {}, []

def sync_local_beatmaps_task():
    """The background task for syncing the local beatmap database."""
    progress = TASK_PROGRESS['sync']
    progress['status'] = 'running'
    progress['current'] = 0
    progress['total'] = 0
    progress['message'] = 'Starting beatmap sync...'
    progress['batches_done'] = 0
    
    BATCH_SIZE = 500

    try:
        osu_folder = os.getenv('OSU_FOLDER')
        if not osu_folder: raise ValueError("OSU_FOLDER environment variable is not set.")
        
        db_path = os.path.join(osu_folder, 'osu!.db')
        if not os.path.exists(db_path): raise FileNotFoundError(f"osu!.db not found at {db_path}")

        songs_path = os.path.join(osu_folder, 'Songs')
        
        progress['message'] = 'Reading beatmap library (osu!.db)...'
        all_beatmap_data = parser.parse_osu_db(db_path)
        
        progress['message'] = 'Saving basic beatmap metadata...'
        database.add_or_update_beatmaps(all_beatmap_data)
        progress['batches_done'] += 1

        progress['message'] = 'Checking for un-analyzed beatmaps...'
        processed_md5s = database.get_processed_beatmap_hashes()
        
        items_to_process = [
            (md5, data) for md5, data in all_beatmap_data.items() 
            if md5 not in processed_md5s and data.get('game_mode') == 0
        ]
        
        if not items_to_process:
            progress['status'] = 'complete'
            progress['message'] = 'No new beatmaps to analyze. Your library is up to date.'
            return
            
        # --- Stage 1: File Verification ---
        progress['total'] = len(items_to_process)
        progress['current'] = 0
        progress['message'] = f"Step 1/2: Verifying {progress['total']} beatmap files..."
        
        verified_items = []
        for i, (md5, beatmap) in enumerate(items_to_process):
            progress['current'] = i + 1
            if beatmap.get('folder_name') and beatmap.get('osu_file_name'):
                osu_file_path = os.path.join(songs_path, beatmap['folder_name'], beatmap['osu_file_name'])
                if os.path.exists(osu_file_path):
                    verified_items.append((md5, beatmap, osu_file_path))

        # --- Stage 2: Analysis ---
        progress['total'] = len(verified_items)
        progress['current'] = 0
        if progress['total'] == 0:
            progress['status'] = 'complete'
            progress['message'] = 'Beatmap library is up to date. No new files found to analyze.'
            return
            
        progress['message'] = f"Step 2/2: Analyzing {progress['total']} beatmaps..."
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            tasks = {
                executor.submit(process_osu_file_and_cache, osu_path, bmap.get('bpm', 0), md5): md5
                for md5, bmap, osu_path in verified_items
            }

            processed_batch = {}
            mod_cache_batch = []
            for future in concurrent.futures.as_completed(tasks):
                progress['current'] += 1
                progress['message'] = f"Step 2/2: Analyzing beatmaps ({progress['current']}/{progress['total']})"
                try:
                    md5, result_data, mod_caches = future.result()
                    if result_data:
                        current_beatmap_data = all_beatmap_data[md5]
                        current_beatmap_data.update(result_data)
                        processed_batch[md5] = current_beatmap_data
                    if mod_caches:
                        mod_cache_batch.extend(mod_caches)
                    
                    if len(processed_batch) >= BATCH_SIZE:
                        progress['message'] = f"Step 2/2: Saving progress... ({progress['current']}/{progress['total']})"
                        database.add_or_update_beatmaps(processed_batch)
                        database.add_beatmap_mod_cache(mod_cache_batch)
                        progress['batches_done'] += 1
                        processed_batch = {}
                        mod_cache_batch = []
                except Exception as e:
                    logging.error(f"Error processing beatmap future for md5 {tasks[future]}: {e}", exc_info=True)

        if processed_batch:
            database.add_or_update_beatmaps(processed_batch)
            progress['batches_done'] += 1
        if mod_cache_batch:
            database.add_beatmap_mod_cache(mod_cache_batch)
        
        progress['status'] = 'complete'
        progress['message'] = 'Sync complete! Your beatmap library is up to date.'
    except Exception as e:
        logging.error(f"Error in sync task: {e}", exc_info=True)
        progress['status'] = 'error'
        progress['message'] = f'Sync failed: {e}'

def scan_replays_task():
    """The background task for scanning the replays folder."""
    progress = TASK_PROGRESS['scan']
    progress['status'] = 'running'
    progress['current'] = 0
    progress['total'] = 0
    progress['message'] = 'Starting replay scan...'

    BATCH_SIZE = 200 # Define batch size for DB writes

    try:
        osu_folder = os.getenv('OSU_FOLDER')
        if not osu_folder: raise ValueError("OSU_FOLDER path not set in .env file")
        
        replays_path = os.path.join(osu_folder, 'Data', 'r')
        songs_path = os.path.join(osu_folder, 'Songs')
        if not os.path.isdir(replays_path): raise FileNotFoundError(f"Replays directory not found at: {replays_path}")

        all_beatmaps = {b['md5_hash']: b for b in database.get_all_beatmaps(limit=100000)['beatmaps']}
        if not all_beatmaps: logging.warning("Beatmap DB is empty. Replay data may be incomplete.")

        progress['message'] = 'Checking for existing replays in database...'
        existing_replay_md5s = database.get_all_replay_md5s()
        all_replay_files = [f for f in os.listdir(replays_path) if f.endswith('.osr')]
        replay_files_to_process = [f for f in all_replay_files if f[:-4] not in existing_replay_md5s]
        
        progress['total'] = len(replay_files_to_process)
        if progress['total'] == 0:
            progress['status'] = 'complete'
            progress['message'] = 'No new replays found. Your scores are up to date.'
            return

        progress['message'] = f"Found {progress['total']} new replays to process..."
        replay_batch = []

        for i, file_name in enumerate(replay_files_to_process):
            progress['current'] = i + 1
            progress['message'] = f"Processing replays: {progress['current']}/{progress['total']}"
            
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
                
                replay_batch.append(replay_data)
                
                if len(replay_batch) >= BATCH_SIZE:
                    progress['message'] = f"Saving a batch of replays... ({progress['current']}/{progress['total']})"
                    database.add_replays_batch(replay_batch)
                    replay_batch = [] # Reset the batch
            except Exception as e:
                logging.error(f"Could not process file {file_name}: {e}", exc_info=True)
        
        if replay_batch:
            progress['message'] = 'Finalizing scan...'
            database.add_replays_batch(replay_batch)
        
        progress['status'] = 'complete'
        progress['message'] = f"Scan complete! Added {progress['total']} new replays to your library."
    except Exception as e:
        logging.error(f"Error in scan task: {e}", exc_info=True)
        progress['status'] = 'error'
        progress['message'] = f'Scan failed: {e}'