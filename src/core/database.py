"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/database.py
Centralized SQLAlchemy Base and AuditMixin to avoid circular dependencies.
Author : triqbit
License: MIT
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AuditMixin:
    """Audit columns as per DATABASE_STANDARDS.md."""

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    is_deleted = Column(Boolean, default=False)
