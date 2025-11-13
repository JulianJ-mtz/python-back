# Python Back API

FastAPI backend application with PostgreSQL/Supabase database.

## Setup

1. Install Poetry (if not already installed):

    ```bash
    curl -sSL https://install.python-poetry.org | python3 -
    ```

2. Install dependencies:
    ```bash
    poetry install
    ```

3. Configure environment variables:
    ```bash
    cp .env.example .env
    ```
    
    Edit `.env` and set your configuration:
    - `SECRET_KEY`: Required for JWT token signing (use a strong random string)
    - `DATABASE_URL`: Your Supabase connection string or local PostgreSQL URL

## Database Configuration

### Using Supabase (Recommended for Production)

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Go to Project Settings > Database
3. Copy the "Connection string" with **Connection pooling** enabled (port 6543)
4. Set it in your `.env` file:
   ```
   DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
   ```

**Important Supabase Notes:**
- Always use the **connection pooler** (port 6543) instead of direct connection (port 5432)
- The app is optimized with smaller connection pool sizes since Supabase has its own pooler
- Connection pool configuration: 5 connections, max overflow 10
- Connections are recycled every 5 minutes
- Automatic connection health checks enabled (`pool_pre_ping=True`)

### Using Local PostgreSQL (Development)

If `DATABASE_URL` is not set, the app falls back to:
```
postgresql://postgres:root@localhost:5432/py-db
```

## Database Migrations

This project uses Alembic for database migrations:

```bash
# Create a new migration after schema changes
alembic revision --autogenerate -m "description of changes"

# Apply migrations to database
alembic upgrade head

# Check current migration status
alembic current

# View migration history
alembic history
```

**Important:** Never create tables manually with `Base.metadata.create_all()`. Always use Alembic migrations.

## Running the Application

```bash
poetry run fastapi dev src/app/main.py
```

The application will run on `http://localhost:8000` by default.

-   API Documentation: `http://localhost:8000/docs`
-   Health Check: `http://localhost:8000/health` (includes database connectivity test)

## Project Structure

```
src/app/
├── routes/          # API endpoints (FastAPI routers)
├── services/        # Business logic and database operations
├── models/          # SQLAlchemy ORM models
├── schemas.py       # Pydantic models for validation
├── dependencies.py  # FastAPI dependencies (auth, DB sessions)
├── database.py      # Database connection and configuration
└── utils/           # Custom exceptions and utilities
```

## Best Practices

### Connection Pooling
- The app uses SQLAlchemy's QueuePool with optimized settings for Supabase
- Connections are validated before use (`pool_pre_ping=True`)
- Automatic connection recycling prevents stale connections
- TCP keepalive configured for better connection stability

### Error Handling
- Database errors are caught and logged in `get_db()` dependency
- Custom exceptions for authentication and resource errors
- Global exception handlers for consistent API responses

### Security
- JWT-based authentication with access and refresh tokens
- Access tokens expire after 60 minutes (configurable)
- Refresh tokens expire after 7 days (configurable)
- Passwords hashed with bcrypt
- Protected endpoints use `get_current_user` dependency

## Troubleshooting

### Database Connection Issues

1. **Check connectivity:**
   ```bash
   curl http://localhost:8000/health
   ```
   Should return: `{"status": "healthy", "database": "connected", "api": "ok"}`

2. **Verify DATABASE_URL:**
   - Ensure it's using the connection pooler (port 6543)
   - Check credentials are correct
   - Verify Supabase project is not paused

3. **Check logs:**
   The application logs database connection events and errors

### Migration Issues

If migrations fail:
```bash
# Check current state
alembic current

# View pending migrations
alembic history

# Reset to a specific version
alembic downgrade <revision>
```

## Environment Variables

Required:
- `SECRET_KEY` - JWT signing key (must be set)
- `DATABASE_URL` - Database connection string (optional, falls back to local)

Optional with defaults:
- `ALGORITHM` - JWT algorithm (default: HS256)
- `MINUTES_TOKEN_EXPIRE` - Access token TTL (default: 60)
- `DAYS_REFRESH_TOKEN_EXPIRE` - Refresh token TTL (default: 7)

See `.env.example` for complete configuration template.
