"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/database.py
Central database utilities and shared SQLAlchemy Base.
Author : triqbit
License: MIT
"""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class AuditMixin:
    """Audit columns as per DATABASE_STANDARDS.md."""

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    is_deleted = Column(Boolean, default=False)
