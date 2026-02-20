"""
Database configuration and base model.

Uses SQLAlchemy 2.0 declarative style with SQLite.
"""

from pathlib import Path
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

import appdirs


def get_database_path() -> Path:
    """Get the path to the SQLite database file."""
    # Use appdirs for cross-platform data directory
    data_dir = Path(appdirs.user_data_dir("AmpsMotion", "AmpeSports"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "ampsmotion.db"


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# Database engine with WAL mode for better performance
DATABASE_URL = f"sqlite:///{get_database_path()}"
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},  # Allow multi-threaded access
)

# Session factory
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager for database sessions."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Initialize the database, creating all tables."""
    Base.metadata.create_all(bind=engine)


def reset_db() -> None:
    """Drop and recreate all tables. USE WITH CAUTION."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
