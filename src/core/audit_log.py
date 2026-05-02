"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/audit_log.py
Audit logging system for production traceability.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, Integer, JSON, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
logger = logging.getLogger(__name__)


class AuditCategory(str, Enum):
    CONFIG = "CONFIG"
    RISK = "RISK"
    MODEL = "MODEL"
    OPERATOR = "OPERATOR"
    RELEASE = "RELEASE"


class AuditEntry(Base):
    """Audit Trail record for compliance and traceability."""

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
    category = Column(String(20), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    actor = Column(String(50), nullable=False)
    description = Column(Text)
    metadata_json = Column(JSON)


class AuditLogger:
    """
    Singleton Audit Logger for recording critical system events.
    Ensures a tamper-evident record of decisions and configuration changes.
    """

    _instance: Optional[AuditLogger] = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AuditLogger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_url: Optional[str] = None) -> None:
        if self._initialized:
            return

        if not db_url:
            # Fallback for retrieval after initialization
            return

        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self._initialized = True
        logger.info("AuditLogger initialized | db=%s", db_url)

    def log(
        self,
        category: AuditCategory,
        event_type: str,
        description: str,
        actor: str = "SYSTEM",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a new audit entry."""
        if not self._initialized:
            logger.warning("AuditLogger not initialized. Event dropped: %s", event_type)
            return

        try:
            with self.Session() as session:
                entry = AuditEntry(
                    category=category.value,
                    event_type=event_type,
                    actor=actor,
                    description=description,
                    metadata_json=metadata or {},
                )
                session.add(entry)
                session.commit()
        except Exception as e:
            logger.error("Failed to write audit log: %s", e)


def get_audit_logger() -> AuditLogger:
    """Retrieves the global AuditLogger instance."""
    return AuditLogger()
