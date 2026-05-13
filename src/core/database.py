"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/database.py
Centralized database engine and session management.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Harden SQLite connections by enabling foreign keys and WAL mode.
    Only applied to SQLite connections.
    """
    import sqlite3

    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
        logger.debug("SQLite pragmas (foreign_keys, WAL) enabled.")


@lru_cache(maxsize=16)
def get_engine(db_url: str) -> Engine:
    """
    Create and return a cached SQLAlchemy engine.
    Aligned with DATABASE_STANDARDS.md for connection pooling and resilience.
    """
    is_sqlite = db_url.startswith("sqlite")

    connect_args: dict[str, Any] = {}
    if is_sqlite:
        # SQLite specific optimizations
        connect_args["check_same_thread"] = False

    # Use appropriate pooling based on database type and environment.
    from sqlalchemy.pool import NullPool, QueuePool, StaticPool

    engine_kwargs: dict[str, Any] = {
        "pool_pre_ping": True,  # Verify connections are alive
        "pool_recycle": 3600,  # Recycle connections every hour
        "connect_args": connect_args,
        "echo": False,
    }

    if is_sqlite:
        # sqlite:///:memory: requires StaticPool to share the same database across connections.
        # File-based SQLite works best with NullPool to avoid "database is locked" errors in many setups.
        if db_url == "sqlite://" or ":memory:" in db_url:
            engine_kwargs["poolclass"] = StaticPool
        else:
            engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["poolclass"] = QueuePool
        engine_kwargs["pool_size"] = 20
        engine_kwargs["max_overflow"] = 40

    engine = create_engine(db_url, **engine_kwargs)

    logger.info(
        "Database engine initialized for: %s", db_url.split("@")[-1] if "@" in db_url else db_url
    )
    return engine


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a session factory for the provided engine."""
    return sessionmaker(bind=engine, expire_on_commit=False)


def verify_engine(engine: Engine) -> bool:
    """Perform a low-level ping to verify database connectivity."""
    try:
        with engine.connect() as conn:
            # Dialect-neutral ping
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("Database engine verification failed: %s", e)
        return False
