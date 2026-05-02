"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/audit_log.py
Enterprise audit trail system for compliance and post-incident review.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    JSON,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
logger = logging.getLogger(__name__)


class AuditCategory(str, Enum):
    CONFIG = "CONFIG"
    RISK = "RISK"
    MODEL = "MODEL"
    OPERATOR = "OPERATOR"
    RELEASE = "RELEASE"


class AuditEntry(Base):
    """
    Logs critical system decisions and events for auditability.
    """

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
    category = Column(String(50), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    actor = Column(String(100), default="system")
    description = Column(Text)
    metadata_json = Column(JSON)  # Stores detailed context as JSON

    def __repr__(self) -> str:
        return f"<AuditEntry(id={self.id}, category={self.category}, event_type={self.event_type})>"


class AuditLogger:
    """
    Centralized logger for compliance-grade audit trails.
    """

    _instance: Optional[AuditLogger] = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AuditLogger, cls).__new__(cls)
        return cls._instance

    def __init__(self, db_url: Optional[str] = None) -> None:
        # Avoid re-initialization if already initialized
        if hasattr(self, "engine"):
            return

        if db_url is None:
            # Fallback to default if not provided during first call
            db_url = "sqlite:///trades.db"

        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        logger.info("AuditLogger initialized | db=%s", db_url)

    def log(
        self,
        category: AuditCategory,
        event_type: str,
        description: str,
        actor: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Record a new audit entry.
        """
        try:
            with self.Session() as session:
                entry = AuditEntry(
                    category=category.value,
                    event_type=event_type,
                    description=description,
                    actor=actor,
                    metadata_json=metadata,
                )
                session.add(entry)
                session.commit()
                return entry.id
        except Exception as e:
            logger.error("Failed to write to audit log: %s", e)
            return -1

    def log_config_change(self, key: str, old_value: Any, new_value: Any, reason: str) -> int:
        return self.log(
            AuditCategory.CONFIG,
            "CHANGE",
            f"Configuration {key} changed: {old_value} -> {new_value}",
            metadata={"key": key, "old_value": old_value, "new_value": new_value, "reason": reason},
        )

    def log_risk_decision(self, decision: str, reason: str, metadata: Dict[str, Any]) -> int:
        return self.log(
            AuditCategory.RISK,
            "DECISION",
            f"Risk Decision: {decision} - {reason}",
            metadata=metadata,
        )

    def log_model_prediction(self, model_name: str, outcome: Any, confidence: float, metadata: Dict[str, Any]) -> int:
        return self.log(
            AuditCategory.MODEL,
            "PREDICTION",
            f"Model {model_name} predicted {outcome} with {confidence:.2f} confidence",
            metadata=metadata,
        )

    def log_operator_action(self, action: str, description: str, actor: str = "operator") -> int:
        return self.log(
            AuditCategory.OPERATOR,
            "ACTION",
            description,
            actor=actor,
            metadata={"action": action},
        )

    def log_release_event(self, version: str, event: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        return self.log(
            AuditCategory.RELEASE,
            "EVENT",
            f"Release {version}: {event}",
            metadata=metadata or {"version": version, "event": event},
        )


def get_audit_logger(db_url: Optional[str] = None) -> AuditLogger:
    """Singleton accessor for AuditLogger."""
    return AuditLogger(db_url)
