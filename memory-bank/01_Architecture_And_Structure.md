# 1. Architecture and Structure

## 1.1. Guiding Principles

This project follows a modular and maintainable architecture. The backend is decoupled from the frontend, communicating via a clear API. This allows for independent development and testing.

## 1.2. Technology Stack

-   **Backend Language:** **Python 3.10+**. It's a high-performance, well-documented language with excellent support for binary data parsing and web frameworks. (Source: User Request)
-   **Backend Framework:** **Flask**. A lightweight and flexible web framework, perfect for creating a simple REST API to serve the score data.
-   **Database:** **SQLite**. A serverless, self-contained SQL database engine. It's ideal for a local application as it doesn't require a separate server process and is stored in a single file.
-   **Frontend:** **HTML, CSS, and vanilla JavaScript**. As requested, this provides a simple, universal interface for displaying the data. (Source: User Request)

## 1.3. Project Directory Structure

```
/
├── memory-bank/
│   └── 01_Architecture_And_Structure.md
├── backend/
│   ├── app.py             # Main Flask application, API endpoints
│   ├── database.py        # Database connection and schema setup
│   ├── parser.py          # .osr file parsing logic
│   └── requirements.txt   # Python dependencies
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── script.js
└── replays/               # Directory where users will place .osr files
```