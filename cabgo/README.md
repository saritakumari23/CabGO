# CabGo - Ride Hailing Application

This project is a cab booking application with a Flask backend and a Vue.js frontend.

## Project Structure

- `backend/`: Contains the Flask application.
  - `app/`: The main application package.
    - `__init__.py`: App factory (`create_app`).
    - `config.py`: Application configuration.
    - `models/`: SQLAlchemy models (to be created).
    - `routes/` or individual blueprint files (e.g., `auth.py`): Route definitions (to be created).
  - `migrations/`: Database migration scripts (if using Flask-Migrate).
  - `requirements.txt`: Python dependencies.
  - `.flaskenv`: Environment variables for Flask.
  - `run.py` (optional): Script to run the Flask app.
- `frontend/`: Contains the Vue.js application (to be created).

## Backend Setup

1.  Navigate to the `backend` directory:
    ```bash
    cd backend
    ```
2.  Create a virtual environment:
    ```bash
    python -m venv venv
    ```
3.  Activate the virtual environment:
    - Windows:
      ```bash
      .\venv\Scripts\activate
      ```
    - macOS/Linux:
      ```bash
      source venv/bin/activate
      ```
4.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
5.  (Optional, if using Flask-Migrate) Initialize database migrations:
    ```bash
    # flask db init # Only once per project
    # flask db migrate -m "Initial migration."
    # flask db upgrade
    ```
6.  Create a `.env` file in the `backend` directory for sensitive configurations (e.g., `SECRET_KEY`, `DATABASE_URL`):
    ```env
    SECRET_KEY='your_strong_secret_key'
    # DATABASE_URL='postgresql://user:password@host:port/database'
    ```
7.  Run the Flask development server:
    ```bash
    flask run
    ```
    The backend should be running on `http://127.0.0.1:5000`.

## Frontend Setup (To be detailed later)

---

This README will be updated as the project progresses.
