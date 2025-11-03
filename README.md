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

```bash
 poetry run fastapi dev src/app/main.py
```

## Development

The application will run on `http://localhost:8000` by default.

-   API Documentation: `http://localhost:8000/docs`
-   Health Check: `http://localhost:8000/health`

## Environment

Make sure your PostgreSQL database is running and accessible at the connection string configured in `src/app/database.py`.
