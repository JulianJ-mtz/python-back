# Python Back API

FastAPI backend application.

## Setup

1. Install Poetry (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```

## Running the Application

### Option 1: Using Poetry run (recommended)
```bash
poetry run uvicorn src.main:app --reload
```

### Option 2: Activate Poetry shell and run
```bash
poetry shell
uvicorn src.main:app --reload
```

## Development

The application will run on `http://localhost:8000` by default.

- API Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

## Environment

Make sure your PostgreSQL database is running and accessible at the connection string configured in `src/db.py`.
