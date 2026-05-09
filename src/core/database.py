"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/database.py
Centralized database management and session handling.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, pool
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Unified SQLAlchemy 2.0 DeclarativeBase."""

    pass


class DatabaseManager:
    """
    Manages database connections, engine creation, and session factories.
    """

    _instance: DatabaseManager | None = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_url: str | None = None) -> None:
        if self._initialized:
            return

        if not db_url:
            raise ValueError("DatabaseManager must be initialized with a db_url")

        # Connection pooling configuration aligned with DATABASE_STANDARDS.md
        pool_kwargs = {
            "pool_pre_ping": True,
            "pool_recycle": 3600,
        }

        # SQLite does not support pool_size and max_overflow in the same way
        if "sqlite" not in db_url:
            pool_kwargs.update(
                {
                    "pool_size": 20,
                    "max_overflow": 40,
                    "poolclass": pool.QueuePool,
                }
            )
        else:
            # For SQLite, StaticPool is often used for in-memory,
            # but for file-based, we might want NullPool or just default.
            # However, for consistency in the app and to support multi-threading:
            pool_kwargs["poolclass"] = pool.StaticPool
            # Important for SQLite multi-threaded access (e.g. in tests with FastAPI TestClient)
            pool_kwargs["connect_args"] = {"check_same_thread": False}

        self.engine = create_engine(db_url, **pool_kwargs)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self._initialized = True
        logger.info("DatabaseManager initialized with database: %s", db_url)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @classmethod
    def get_instance(cls) -> DatabaseManager:
        """Retrieve the singleton instance of the DatabaseManager."""
        if cls._instance is None or not cls._instance._initialized:
            raise RuntimeError(
                "DatabaseManager not initialized. Call DatabaseManager(db_url) first."
            )
        return cls._instance


def get_db_manager() -> DatabaseManager:
    """Convenience function to retrieve the DatabaseManager."""
    return DatabaseManager.get_instance()
