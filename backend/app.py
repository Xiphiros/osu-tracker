import os
import sys
import logging
import threading
import webview
import signal
from flask import Flask, send_from_directory
from flask_cors import CORS

# Import configurations and modular components
from config import IS_BUNDLED, static_folder_path
from api.routes import api_blueprint
import database

# --- Flask App Initialization ---
app = Flask(__name__, static_folder=static_folder_path, static_url_path='')
CORS(app)
app.register_blueprint(api_blueprint)

# --- Frontend Serving ---
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_index(path):
    """Serves the frontend application."""
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
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

    # Create the pywebview window to display the frontend
    window = webview.create_window(
        'osu! Local Score Tracker',
        'http://127.0.0.1:5000',
        width=1280,
        height=800,
        resizable=True,
        min_size=(960, 600)
    )

    def on_closing():
        """Handle window closing event to gracefully shut down the app."""
        logging.info("Webview window is closing. Shutting down application.")
        if not IS_BUNDLED:
            # In development, a SIGINT is needed to stop the Flask server
            os.kill(os.getpid(), signal.SIGINT)

    window.events.closing += on_closing

    # Start the pywebview event loop
    webview.start(debug=not IS_BUNDLED)