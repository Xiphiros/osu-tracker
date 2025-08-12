# 1. Architecture and Structure

## 1.1. Guiding Principles

This project follows a modular and maintainable architecture. The backend is decoupled from the frontend, communicating via a clear API. This allows for independent development and testing.

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
├── memory-bank/
│   └── 01_Architecture_And_Structure.md
├── backend/
│   ├── app.py              # Main Flask application and pywebview entry point
│   ├── database.py         # Database connection and schema setup
│   ├── parser.py           # File parsing logic for .osr and .db
│   └── requirements.txt
├── frontend/
│   ├── ... (contents unchanged)
├── .env                    # Environment variables (e.g., OSU_FOLDER)
├── .gitignore
└── build.py                # Script to build the executable
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