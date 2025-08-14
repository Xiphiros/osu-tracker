import time
import logging
import os
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import database
import parser
from config import IS_BUNDLED
from utils import get_safe_join

# This will hold the pywebview window object once the app starts
window = None

def process_new_replay(file_path):
    """Processes a single newly created replay file."""
    # Add a small delay to ensure the file is fully written by osu!
    time.sleep(1 if IS_BUNDLED else 0.5)

    logging.info(f"New replay detected: {os.path.basename(file_path)}")
    try:
        osu_folder = os.getenv('OSU_FOLDER')
        if not osu_folder:
            logging.error("Cannot process new replay, OSU_FOLDER not set.")
            return

        replay_data = parser.parse_replay_file(file_path)
        if not replay_data or not replay_data.get('replay_md5'):
            logging.warning(f"Could not parse new replay file (it may be incomplete): {file_path}")
            return
        
        beatmap_info = database.get_beatmap_by_md5(replay_data['beatmap_md5'])
        if beatmap_info:
            folder_name = beatmap_info.get('folder_name')
            osu_file = beatmap_info.get('osu_file_name')
            songs_path = os.path.join(osu_folder, 'Songs')
            osu_file_path = get_safe_join(songs_path, folder_name, osu_file)

            if osu_file_path and os.path.exists(osu_file_path):
                pp_info = parser.calculate_pp(osu_file_path, replay_data)
                replay_data.update(pp_info)
                osu_details = parser.parse_osu_file(osu_file_path)
                replay_data.update(osu_details)
        
        database.add_replay(replay_data)
        logging.info(f"Successfully processed and added new replay for {replay_data.get('player_name')}.")

        # Notify the frontend that data has changed, triggering a UI refresh
        if window:
            window.evaluate_js("document.dispatchEvent(new CustomEvent('datachanged', { bubbles: true }))")
            logging.info("Dispatched 'datachanged' event to frontend.")

    except Exception as e:
        logging.error(f"Error processing new replay {file_path}: {e}", exc_info=True)

class ReplayEventHandler(FileSystemEventHandler):
    """Handles file system events for the replays folder."""
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.osr'):
            # Run processing in a new thread to avoid blocking the watchdog observer
            thread = threading.Thread(target=process_new_replay, args=(event.src_path,))
            thread.daemon = True
            thread.start()

def start_watching(osu_folder_path, window_obj):
    """Initializes and starts the file system watcher."""
    global window
    window = window_obj

    if not osu_folder_path:
        logging.warning("osu! folder not set. Watchdog service will not start.")
        return

    replays_path = os.path.join(osu_folder_path, 'Data', 'r')
    if not os.path.isdir(replays_path):
        logging.error(f"Replays directory not found at: {replays_path}. Watchdog will not start.")
        return

    event_handler = ReplayEventHandler()
    observer = Observer()
    observer.schedule(event_handler, replays_path, recursive=False)
    
    observer.start()
    logging.info(f"Watchdog service started, monitoring: {replays_path}")

    try:
        while observer.is_alive():
            observer.join(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()