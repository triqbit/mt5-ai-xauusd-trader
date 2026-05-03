"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/audit_log.py
Enterprise audit logging system for production traceability.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    DateTime,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 DeclarativeBase."""

    pass


class AuditEntry(Base):
    """
    Audit log entry for recording system actions and events.
    Aligned with enterprise traceability requirements.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    actor: Mapped[str] = mapped_column(String(100), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class AuditLogger:
    """
    Singleton AuditLogger for managing system audit traces.
    """

    _instance: Optional[AuditLogger] = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_url: Optional[str] = None) -> None:
        if self._initialized:
            return

        if not db_url:
            raise ValueError("AuditLogger must be initialized with a db_url")

        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self._initialized = True
        logger.info("AuditLogger initialized with database: %s", db_url)

    def log(self, actor: str, action: str, details: Optional[str] = None) -> int:
        """
        Record a new audit entry.
        """
        with self.Session() as session:
            entry = AuditEntry(
                actor=actor,
                action=action,
                details=details,
            )
            session.add(entry)
            session.commit()
            return entry.id

    @classmethod
    def get_instance(cls) -> AuditLogger:
        """
        Retrieve the singleton instance of the AuditLogger.
        """
        if cls._instance is None or not cls._instance._initialized:
            raise RuntimeError("AuditLogger not initialized. Call AuditLogger(db_url) first.")
        return cls._instance


def get_audit_logger() -> AuditLogger:
    """
    Convenience function to retrieve the AuditLogger.
    """
    return AuditLogger.get_instance()
