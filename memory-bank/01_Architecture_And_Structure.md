# 1. Architecture and Structure

## 1.1. Guiding Principles

This project follows a modular and maintainable architecture. The backend is decoupled from the frontend, communicating via a clear API. This allows for independent development and testing.

## 1.2. Technology Stack

-   **Backend Language:** **Python 3.10+**. It's a high-performance, well-documented language with excellent support for binary data parsing and web frameworks. (Source: User Request)
-   **Backend Framework:** **Flask**. A lightweight and flexible web framework, perfect for creating a simple REST API to serve the score data.
-   **Database:** **SQLite**. A serverless, self-contained SQL database engine. It's ideal for a local application as it doesn't require a separate server process and is stored in a single file.
-   **Frontend:** **HTML, CSS, and vanilla JavaScript (ES6 Modules)**. This provides a simple, universal interface for displaying the data. The frontend is structured modularly to separate concerns. (Source: User Request)

## 1.3. Project Directory Structure

```
/
├── memory-bank/
│   └── 01_Architecture_And_Structure.md
├── backend/
│   ├── app.py              # Main Flask application, API endpoints
│   ├── database.py         # Database connection and schema setup
│   ├── parser.py           # File parsing logic for .osr and .db
│   └── requirements.txt
├── frontend/
│   ├── assets/             # Global assets (e.g., CSS, images)
│   │   └── css/
│   │       └── main.css
│   ├── components/         # Reusable UI components (e.g., ReplayCard)
│   ├── services/           # Modules for backend communication (e.g., api.js)
│   ├── views/              # Main content for different pages/tabs
│   ├── index.html          # Main HTML application shell
│   └── main.js             # Application entry point, routing
└── .env                    # Environment variables (e.g., OSU_FOLDER)
```