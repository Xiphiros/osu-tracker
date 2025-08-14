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
    "sync": {"status": "idle", "current": 0, "total": 0, "message": ""},
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
    progress['message'] = 'Initializing...'
    
    BATCH_SIZE = 500  # Define batch size for DB writes and in-memory processing

    try:
        osu_folder = os.getenv('OSU_FOLDER')
        if not osu_folder: raise ValueError("OSU_FOLDER environment variable is not set.")
        
        db_path = os.path.join(osu_folder, 'osu!.db')
        if not os.path.exists(db_path): raise FileNotFoundError(f"osu!.db not found at {db_path}")

        songs_path = os.path.join(osu_folder, 'Songs')
        
        progress['message'] = 'Parsing osu!.db...'
        all_beatmap_data = parser.parse_osu_db(db_path)
        all_beatmap_items = list(all_beatmap_data.items())
        progress['total'] = len(all_beatmap_items)
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Process beatmaps in chunks to manage memory
            for i in range(0, len(all_beatmap_items), BATCH_SIZE):
                chunk_items = all_beatmap_items[i:i + BATCH_SIZE]
                chunk_data = dict(chunk_items)
                tasks = []

                for md5, beatmap in chunk_data.items():
                    if beatmap.get('folder_name') and beatmap.get('osu_file_name') and beatmap.get('game_mode') == 0:
                        osu_file_path = os.path.join(songs_path, beatmap['folder_name'], beatmap['osu_file_name'])
                        if os.path.exists(osu_file_path):
                            tasks.append((osu_file_path, beatmap.get('bpm', 0), md5))

                if not tasks:
                    progress['current'] += len(chunk_items)
                    continue

                progress['message'] = f"Calculating difficulty for beatmaps {i+1}-{min(i+BATCH_SIZE, len(all_beatmap_items))}..."
                
                future_to_md5 = {executor.submit(process_osu_file_and_cache, path, bpm, md5): md5 for path, bpm, md5 in tasks}
                
                all_mod_caches = []
                for future in concurrent.futures.as_completed(future_to_md5):
                    progress['current'] += 1
                    md5 = future_to_md5[future]
                    
                    try:
                        _md5, result_data, mod_caches = future.result()
                        if result_data:
                            chunk_data[_md5].update(result_data)
                        if mod_caches:
                            all_mod_caches.extend(mod_caches)
                    except Exception as e:
                        beatmap_name = chunk_data.get(md5, {}).get('osu_file_name', 'beatmap')
                        logging.error(f"Error processing future for {beatmap_name}: {e}", exc_info=True)

                # Save the processed chunk to the database
                progress['message'] = f"Saving chunk to database..."
                database.add_or_update_beatmaps(chunk_data)
                if all_mod_caches:
                    database.add_beatmap_mod_cache(all_mod_caches)
        
        progress['status'] = 'complete'
        progress['message'] = 'Beatmap database synchronization complete.'
    except Exception as e:
        logging.error(f"Error in sync task: {e}", exc_info=True)
        progress['status'] = 'error'
        progress['message'] = str(e)

def scan_replays_task():
    """The background task for scanning the replays folder."""
    progress = TASK_PROGRESS['scan']
    progress['status'] = 'running'
    progress['current'] = 0
    progress['total'] = 0
    progress['message'] = 'Initializing...'

    BATCH_SIZE = 200 # Define batch size for DB writes

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
        replay_batch = []

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
                
                replay_batch.append(replay_data)
                
                if len(replay_batch) >= BATCH_SIZE:
                    progress['message'] = f"Writing a batch of {len(replay_batch)} replays to DB..."
                    database.add_replays_batch(replay_batch)
                    replay_batch = [] # Reset the batch
            except Exception as e:
                logging.error(f"Could not process file {file_name}: {e}", exc_info=True)
        
        # Write any remaining replays in the last batch
        if replay_batch:
            progress['message'] = f"Writing final batch of {len(replay_batch)} replays to DB..."
            database.add_replays_batch(replay_batch)
        
        progress['status'] = 'complete'
        progress['message'] = f"Scan complete. Processed {progress['total']} replays."
    except Exception as e:
        logging.error(f"Error in scan task: {e}", exc_info=True)
        progress['status'] = 'error'
        progress['message'] = str(e)