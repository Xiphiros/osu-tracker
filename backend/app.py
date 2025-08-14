import os
import sys
import logging
import threading
import webview
import signal
import shutil
import sqlite3
from flask import Flask, send_from_directory, abort
from flask_cors import CORS

# Import configurations and modular components
from config import IS_BUNDLED, static_folder_path, BASE_DIR
from api.routes import api_blueprint
import database
import watcher

# --- Globals ---
# This will hold the pywebview window instance, accessible by the Api class.
window = None

# --- pywebview API for native functionality ---
class Api:
    def export_database_dialog(self):
        """Opens a native 'Save As' dialog to export the database."""
        try:
            db_path = os.path.join(BASE_DIR, database.DATABASE_FILE)
            if not os.path.exists(db_path):
                return {"status": "error", "message": "Database file not found."}

            result = window.create_file_dialog(
                webview.SAVE_DIALOG,
                directory=os.path.expanduser('~'),
                save_filename='osu_tracker_backup.db',
                file_types=('Database Files (*.db)',)
            )

            if result:
                # create_file_dialog returns a tuple, even for single files
                save_path = result[0]
                shutil.copy(db_path, save_path)
                logging.info(f"Database exported successfully to {save_path}")
                return {"status": "success", "message": "Database exported successfully."}
            else:
                return {"status": "info", "message": "Export cancelled by user."}

        except Exception as e:
            logging.error(f"Failed to export database via dialog: {e}", exc_info=True)
            return {"status": "error", "message": f"An error occurred: {e}"}

    def import_database_dialog(self):
        """Opens a native 'Open' dialog to import a database."""
        try:
            result = window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=False,
                file_types=('Database Files (*.db)',)
            )

            if not result:
                return {"status": "info", "message": "Import cancelled by user."}

            import_path = result[0]
            db_path = os.path.join(BASE_DIR, database.DATABASE_FILE)
            
            # Validation Step
            try:
                conn = sqlite3.connect(import_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='replays';")
                if cursor.fetchone() is None:
                    raise sqlite3.DatabaseError("Database is missing 'replays' table.")
                conn.close()
            except sqlite3.Error as e:
                logging.warning(f"Invalid database file selected for import: {e}")
                return {"status": "error", "message": f"Invalid database file: {e}"}

            # Replacement Step (app must be restarted to release file lock on Windows)
            shutil.copy(import_path, db_path)
            logging.info(f"Database imported from {import_path}. Restart is required.")
            return {"status": "success", "message": "Database imported. Please restart the application."}

        except Exception as e:
            logging.error(f"Failed to import database via dialog: {e}", exc_info=True)
            return {"status": "error", "message": f"An error occurred: {e}"}

# --- Flask App Initialization ---
app = Flask(__name__, static_folder=static_folder_path, static_url_path='')
CORS(app)
app.register_blueprint(api_blueprint)

# --- Frontend Serving ---
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_index(path):
    """Serves the frontend application."""
    if path == "":
        return send_from_directory(app.static_folder, 'index.html')

    # Prevent directory traversal.
    # The normalized, absolute path of the requested file must be inside the static folder.
    static_folder_abs = os.path.abspath(app.static_folder)
    requested_path_abs = os.path.normpath(os.path.join(static_folder_abs, path))

    if not requested_path_abs.startswith(static_folder_abs):
        # Directory traversal attempt.
        return abort(404)

    # Check if the path points to an existing file.
    if os.path.isfile(requested_path_abs):
        return send_from_directory(app.static_folder, path)
    
    # For any other path, serve the SPA's entry point.
    return send_from_directory(app.static_folder, 'index.html')

# --- Server Execution ---
def run_server():
    """Runs the Flask server using waitress for production bundles."""
    if IS_BUNDLED:
        from waitress import serve
        serve(app, host="127.0.0.1", port=5000)
    else:
        # Use Flask's built-in server for development (with debug=False to avoid reloader issues)
        app.run(host="127.0.0.1", port=5000, debug=False)

# --- Main Application Entry Point ---
if __name__ == '__main__':
    # Initialize the database on startup
    database.init_db()

    # Start the backend server in a separate thread
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    logging.info("Backend server started in a background thread.")
    
    # Create an instance of the API class that will be exposed to Javascript
    api = Api()

    # Create the pywebview window to display the frontend
    window = webview.create_window(
        'osu! Local Score Tracker',
        'http://127.0.0.1:5000',
        width=1280,
        height=800,
        resizable=True,
        min_size=(960, 600),
        js_api=api
    )
    
    # Start the watchdog service to monitor for new replays
    osu_folder = os.getenv("OSU_FOLDER")
    if osu_folder:
        watcher_thread = threading.Thread(target=watcher.start_watching, args=(osu_folder, window))
        watcher_thread.daemon = True
        watcher_thread.start()
    else:
        logging.warning("OSU_FOLDER not set. Automatic replay detection is disabled.")

    def on_closing():
        """Handle window closing event to gracefully shut down the app."""
        logging.info("Webview window is closing. Shutting down application.")
        if not IS_BUNDLED:
            # In development, a SIGINT is needed to stop the Flask server
            os.kill(os.getpid(), signal.SIGINT)

    window.events.closing += on_closing

    # Start the pywebview event loop
    webview.start(debug=not IS_BUNDLED)