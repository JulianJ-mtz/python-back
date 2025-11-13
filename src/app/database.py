import os
import logging

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import QueuePool, NullPool

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

# Detect if running in Vercel/serverless environment
IS_VERCEL = os.getenv("VERCEL") is not None
IS_PRODUCTION = os.getenv("NODE_ENV") == "production"

if DATABASE_URL:
    if DATABASE_URL.startswith("postgresql://"):
        db_url = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
    else:
        db_url = DATABASE_URL

    # Serverless-optimized pool configuration for Vercel/Supabase
    if IS_VERCEL or IS_PRODUCTION:
        pool_class = NullPool  # No connection pooling in serverless
        logger.info("Using serverless database configuration (NullPool)")
        engine_kwargs = {
            "poolclass": pool_class,
            "pool_pre_ping": True,
            "echo": False,
            "connect_args": {
                "connect_timeout": 10,
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
            },
        }
    else:
        # Supabase-specific pool configuration for development
        pool_class = QueuePool
        logger.info("Using Supabase database connection")
        engine_kwargs = {
            "poolclass": pool_class,
            "pool_size": 5,
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle": 300,
            "pool_pre_ping": True,
            "echo": False,
            "connect_args": {
                "connect_timeout": 10,
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
            },
        }
else:
    db_url = "postgresql://postgres:root@localhost:5432/py-db"
    pool_class = QueuePool
    logger.info("Using local PostgreSQL database")
    engine_kwargs = {
        "poolclass": pool_class,
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
        "echo": False,
        "connect_args": {
            "connect_timeout": 10,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        },
    }

try:
    engine = create_engine(db_url, **engine_kwargs)
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log when a new database connection is established."""
    logger.debug("New database connection established")


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    except OperationalError as e:
        logger.error(f"Database operational error: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected database error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def test_connection():
    """Test database connection. Returns True if successful, False otherwise."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False
