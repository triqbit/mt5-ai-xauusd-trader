"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/audit_log.py
Full audit trail system for compliance and debugging.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text

from src.core.trade_logger import AuditMixin, Base

logger = logging.getLogger(__name__)

class AuditLog(Base, AuditMixin):
    """
    Detailed audit log for every critical decision.
    Compliant with regulatory requirements for traceability.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    category = Column(String(50), nullable=False, index=True)  # CONFIG, TRADE, MODEL, RISK, OPERATOR, DEPLOYMENT
    event_type = Column(String(100), nullable=False)
    details = Column(JSON)
    reason = Column(Text)
    operator = Column(String(100), default="SYSTEM")

class AuditLogger:
    """Interface for recording audit events."""

    def __init__(self, session_factory: Any) -> None:
        self.Session = session_factory

    def log(
        self,
        category: str,
        event_type: str,
        details: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
        operator: str = "SYSTEM",
    ) -> None:
        """Record an audit entry to the database."""
        try:
            with self.Session() as session:
                entry = AuditLog(
                    category=category,
                    event_type=event_type,
                    details=details,
                    reason=reason,
                    operator=operator,
                )
                session.add(entry)
                session.commit()
                logger.debug("Audit Log recorded: %s | %s", category, event_type)
        except Exception as exc:
            logger.error("Failed to record audit log: %s", exc)

__all__ = ["AuditLog", "AuditLogger"]
