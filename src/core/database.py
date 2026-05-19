"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/database.py
Centralized database engine and session management.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
import os
import stat
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

# Slow query logging threshold (seconds) as per DATABASE_STANDARDS.md
SLOW_QUERY_THRESHOLD = 1.0


@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Record the start time of a query."""
    context._query_start_time = time.perf_counter()


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log a warning if the query execution time exceeds the threshold."""
    total_time = time.perf_counter() - context._query_start_time
    if total_time > SLOW_QUERY_THRESHOLD:
        logger.warning(
            "Slow query detected: %s (%.2f seconds)",
            statement,
            total_time,
            extra={"duration": total_time, "statement": statement},
        )


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
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        # Enterprise Security: Overwrite deleted data with zeroes
        cursor.execute("PRAGMA secure_delete=ON")
        cursor.close()
        logger.debug(
            "SQLite pragmas (foreign_keys, WAL, busy_timeout, synchronous, secure_delete) enabled."
        )


@lru_cache(maxsize=16)
def get_engine(db_url: str) -> Engine:
    """
    Create and return a cached SQLAlchemy engine.
    Aligned with DATABASE_STANDARDS.md for connection pooling and resilience.
    """
    is_sqlite = db_url.startswith("sqlite")

    # Security: Enforce restrictive file permissions for SQLite databases
    # Robust check for in-memory SQLite to skip file-system operations
    is_memory = ":memory:" in db_url or db_url in ("sqlite://", "sqlite:///")

    if is_sqlite and not is_memory:
        try:
            url = make_url(db_url)
            if url.database:
                db_path = Path(url.database).resolve()
                # Ensure parent directory exists with restrictive permissions
                # Only harden if the parent is not the current working directory
                # to avoid accidental lockouts from the project root.
                cwd = Path.cwd().resolve()
                if db_path.parent != cwd:
                    if not db_path.parent.exists():
                        # Enterprise Security: Restricted access to data directories (0o700)
                        if os.name != "nt":
                            db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                        else:
                            db_path.parent.mkdir(parents=True, exist_ok=True)
                    elif os.name != "nt":
                        # Enforce restrictive permissions on existing parent directory
                        current_mode = stat.S_IMODE(os.stat(db_path.parent).st_mode)
                        if current_mode & (stat.S_IRWXG | stat.S_IRWXO):
                            os.chmod(db_path.parent, 0o700)

                # Pre-create or harden existing file permissions
                if not db_path.exists():
                    # Create with 0o600 (owner read/write only)
                    fd = os.open(db_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                    os.close(fd)
                    logger.info("Initialized secure SQLite database file: %s", db_path)
                else:
                    # Enforce 0o600 on existing file if supported by platform
                    if os.name != "nt":
                        current_mode = stat.S_IMODE(os.stat(db_path).st_mode)
                        if current_mode != 0o600:
                            os.chmod(db_path, 0o600)
                            logger.debug("Hardened permissions on existing database: %s", db_path)
        except Exception as e:
            logger.warning("Failed to enforce secure SQLite permissions: %s", e)

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
