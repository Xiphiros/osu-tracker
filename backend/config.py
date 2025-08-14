import os
import sys
import logging
from dotenv import load_dotenv

# Determine if running in a PyInstaller bundle
IS_BUNDLED = getattr(sys, 'frozen', False)

# --- Path and Environment Setup ---
# Define BASE_DIR for the project root (in dev) or executable dir (in prod)
if IS_BUNDLED:
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Configure logging, use INFO for bundled app, DEBUG for dev
logging.basicConfig(
    level=logging.INFO if IS_BUNDLED else logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Find the .env file using BASE_DIR
env_path = os.path.join(BASE_DIR, '.env')

# Create a dummy .env if it doesn't exist, then load it.
if not os.path.exists(env_path):
    logging.info(f"No .env file found. Creating one at: {env_path}")
    with open(env_path, 'w') as f:
        f.write("# .env file created by osu! Tracker\n")
        f.write("OSU_FOLDER=\n")
        f.write("DEFAULT_PLAYER=\n")

load_dotenv(dotenv_path=env_path)

# Set up the path to the static frontend folder.
if IS_BUNDLED:
    static_folder_path = os.path.join(sys._MEIPASS, 'frontend')
else:
    static_folder_path = os.path.join(BASE_DIR, 'frontend')