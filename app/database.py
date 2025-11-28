# app/database.py

"""
Database Configuration
======================
Handles database connection for both SQLite and PostgreSQL.
Automatically configures based on DATABASE_URL.

SQLite (Development):
    DATABASE_URL=sqlite:///./garbage_tracker.db

PostgreSQL (Production):
    DATABASE_URL=postgresql://user:password@localhost:5432/garbage_tracker
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

from app.config import settings, is_sqlite


# ============ ENGINE CONFIGURATION ============

if is_sqlite():
    # SQLite configuration
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.DEBUG
    )
    
    # Enable foreign keys
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

else:
    # PostgreSQL configuration
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=settings.DEBUG
    )


# ============ SESSION CONFIGURATION ============

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base for models
Base = declarative_base()


# ============ DEPENDENCY ============

def get_db():
    """FastAPI DB session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============ UTILITY FUNCTIONS ============

def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all database tables. USE WITH CAUTION!"""
    Base.metadata.drop_all(bind=engine)


def reset_database():
    """Drop and recreate all tables. USE WITH CAUTION!"""
    drop_tables()
    create_tables()
