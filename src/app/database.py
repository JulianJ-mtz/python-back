import os
import logging

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import QueuePool

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    if DATABASE_URL.startswith("postgresql://"):
        db_url = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
    else:
        db_url = DATABASE_URL

    # Supabase-specific pool configuration
    pool_size = 5
    max_overflow = 10
    pool_timeout = 30
    pool_recycle = 300
    logger.info("Using Supabase database connection")
else:
    db_url = "postgresql://postgres:root@localhost:5432/py-db"
    pool_size = 10
    max_overflow = 20
    pool_timeout = 30
    pool_recycle = 3600
    logger.info("Using local PostgreSQL database")

try:
    engine = create_engine(
        db_url,
        poolclass=QueuePool,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        pool_pre_ping=True,
        echo=False,
        connect_args={
            "connect_timeout": 10,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        },
    )
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
