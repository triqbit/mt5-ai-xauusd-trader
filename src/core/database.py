"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/database.py
Centralized database infrastructure with resilient connection pooling and retry logic.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import functools
import logging
import time
from datetime import UTC, datetime
from typing import Any, Callable, TypeVar

from sqlalchemy import (
    Boolean,
    DateTime,
    Engine,
    String,
    create_engine,
)
from sqlalchemy.exc import OperationalError, StatementError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

logger = logging.getLogger(__name__)

T = TypeVar("T")

class Base(DeclarativeBase):
    """SQLAlchemy 2.0 DeclarativeBase for the entire application."""
    pass

class AuditMixin:
    """Standard audit columns as per DATABASE_STANDARDS.md."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

def create_resilient_engine(db_url: str, **kwargs: Any) -> Engine:
    """
    Create a SQLAlchemy engine with enterprise-grade resilience settings.
    """
    # Default pooling settings for production workloads
    pool_settings = {
        "pool_size": 20,
        "max_overflow": 40,
        "pool_pre_ping": True,  # Verify connection before use
        "pool_recycle": 3600,   # Recycle connections every hour
    }

    # SQLite doesn't support some pooling arguments
    if "sqlite" in db_url:
        pool_settings = {}

    pool_settings.update(kwargs)

    logger.info("Creating resilient database engine | url=%s", db_url.split('@')[-1] if '@' in db_url else db_url)
    return create_engine(db_url, **pool_settings)

def with_db_retry(
    max_retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying database operations on transient failures.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay
            last_exc = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (OperationalError, StatementError) as e:
                    last_exc = e
                    func_name = getattr(func, "__name__", str(func))
                    if attempt == max_retries:
                        logger.error(
                            "Max database retries reached for %s. Error: %s",
                            func_name, e
                        )
                        raise

                    logger.warning(
                        "Database transient error in %s (attempt %d/%d): %s. Retrying in %.2fs...",
                        func_name, attempt + 1, max_retries, e, delay
                    )
                    time.sleep(delay)
                    delay *= backoff_factor

            if last_exc:
                raise last_exc
            return func(*args, **kwargs) # Should not be reached

        return wrapper
    return decorator
