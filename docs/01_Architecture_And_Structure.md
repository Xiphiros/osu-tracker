# 1. Architecture and Structure

## 1.1. Guiding Principles

This project follows a modular and maintainable architecture. The backend is decoupled from the frontend, communicating via a clear REST API. This allows for independent development and testing.

## 1.2. Technology Stack

-   **Backend Language:** **Python 3.10+**.
-   **Backend Framework:** **Flask**. Used to create the REST API.
-   **Desktop Windowing:** **pywebview**. Wraps the web-based UI in a native desktop window, creating a standalone application feel.
-   **Database:** **SQLite**. A serverless, self-contained SQL database engine.
-   **Frontend:** **HTML, CSS, and vanilla JavaScript (ES6 Modules)**. The UI is built with standard web technologies.
-   **Bundler:** **PyInstaller**. Used to package the application into a single executable for Windows.

## 1.3. Project Directory Structure

```
/
├── docs/                           # Project documentation
│   ├── 01_Architecture_And_Structure.md
│   ├── 02_Data_Formats.md
│   ├── 03_rosu-pp-py_Reference.md
│   └── 04_Training_Model_Recommender.md
├── backend/                        # Flask server and core logic
│   ├── api/                      # API blueprint and route definitions
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── app.py                    # Main application entry point (Flask + pywebview)
│   ├── config.py                 # Configuration and environment setup
│   ├── database.py               # Database schema, migrations, and queries
│   ├── parser.py                 # Logic for parsing osu! file formats
│   ├── tasks.py                  # Asynchronous background tasks (scan, sync)
│   └── watcher.py                # Filesystem watcher for new replays
├── frontend/                       # Vanilla JS frontend application
│   ├── assets/                   # CSS and other static assets
│   ├── components/               # Reusable UI components (JS + CSS)
│   ├── services/                 # API call wrappers
│   ├── utils/                    # Helper modules (e.g., audio player, mods)
│   ├── views/                    # Main application views (JS + CSS)
│   ├── index.html                # Main HTML file
│   └── main.js                   # Main frontend entry point
├── .env                            # Environment variables (OSU_FOLDER, etc.)
├── .gitignore
├── build.py                        # PyInstaller build script
└── requirements.txt
```

## 1.4. Build & Deployment

To create a standalone executable (`.exe`), this project uses **PyInstaller**. This bundles the entire Python application, including the backend server and all dependencies, into a single file. The `pywebview` library handles the creation of the application window.

### 1.4.1. How to Build

1.  Ensure all dependencies are installed:
    ```bash
    pip install -r requirements.txt
    ```
2.  Run the build script from the project root:
    ```bash
    python build.py
    ```
3.  The executable will be created in the `dist/` directory.

### 1.4.2. Running the Application

1.  Place the generated `OsuTracker.exe` in any directory.
2.  Create a `.env` file in the same directory with the following content, pointing to your osu! installation (use forward slashes):
    ```
    OSU_FOLDER="C:/Path/To/Your/osu!"
    ```
3.  Run `OsuTracker.exe`. A dedicated application window will open, displaying the user interface. The local database `osu_tracker.db` will be created in this directory.