"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/database.py
Centralized SQLAlchemy infrastructure and enterprise connection pooling.
Author : triqbit
License: MIT
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Engine,
    String,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import QueuePool


class Base(DeclarativeBase):
    """Unified base class for all SQLAlchemy models."""
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


def get_engine(db_url: str, **kwargs: Any) -> Engine:
    """
    Create a SQLAlchemy engine with enterprise connection pooling.

    Args:
        db_url: SQLAlchemy-compatible connection string.
        **kwargs: Additional engine parameters.
    """
    # SQLite does not support QueuePool's pool_size/max_overflow in the same way
    if db_url.startswith("sqlite"):
        return create_engine(db_url, **kwargs)

    return create_engine(
        db_url,
        poolclass=QueuePool,
        pool_size=20,
        max_overflow=40,
        pool_pre_ping=True,
        pool_recycle=3600,
        **kwargs
    )
