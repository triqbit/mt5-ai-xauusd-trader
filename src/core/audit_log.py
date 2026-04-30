"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/audit_log.py
Comprehensive audit trail system for compliance and debugging.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text

from src.core.database import AuditMixin, Base

logger = logging.getLogger(__name__)

class AuditLog(Base, AuditMixin):
    """
    Full audit trail for compliance and debugging.
    Stores every critical decision, configuration change, and operator action.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False)
    event_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), default="INFO")
    actor = Column(String(50), default="SYSTEM")
    description = Column(Text, nullable=False)
    metadata_json = Column(Text)  # Stores JSON string of extra data

    def __repr__(self) -> str:
        return f"<AuditLog(event_type='{self.event_type}', timestamp='{self.timestamp}')>"

class AuditLogger:
    """
    Interface for writing audit logs.
    Ensures every critical decision is attributable, timestamped, and traceable.
    """
    def __init__(self, session_factory: Any) -> None:
        self.Session = session_factory

    def log_event(
        self,
        event_type: str,
        description: str,
        severity: str = "INFO",
        actor: str = "SYSTEM",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Write an audit entry to the database."""
        try:
            with self.Session() as session:
                entry = AuditLog(
                    event_type=event_type,
                    description=description,
                    severity=severity,
                    actor=actor,
                    metadata_json=json.dumps(metadata) if metadata else None
                )
                session.add(entry)
                session.commit()
                logger.debug("Audit log recorded: %s", event_type)
        except Exception as e:
            # We don't want audit logging failure to crash the main loop,
            # but it is a serious issue.
            logger.error("AUDIT LOG FAILURE: %s", e)

    def log_config_change(self, reason: str, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> None:
        """Log a configuration change."""
        self.log_event(
            event_type="CONFIG_CHANGE",
            description=f"Configuration updated: {reason}",
            severity="WARNING",
            metadata={
                "old": old_config,
                "new": new_config
            }
        )

    def log_trade_blocked(self, symbol: str, reason: str, decision_chain: Dict[str, Any]) -> None:
        """Log why a trade was blocked by the risk engine."""
        self.log_event(
            event_type="TRADE_BLOCKED",
            description=f"Trade for {symbol} blocked: {reason}",
            severity="WARNING",
            metadata={
                "symbol": symbol,
                "reason": reason,
                "decision_chain": decision_chain
            }
        )

    def log_prediction(self, symbol: str, direction: int, confidence: float, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log model prediction outcomes."""
        data = {
            "symbol": symbol,
            "direction": direction,
            "confidence": confidence
        }
        if metadata:
            data.update(metadata)

        self.log_event(
            event_type="MODEL_PREDICTION",
            description=f"Model prediction for {symbol}: dir={direction}, conf={confidence:.4f}",
            metadata=data
        )

    def log_operator_action(self, action: str, reason: str, actor: str = "ADMIN") -> None:
        """Log manual operator actions (overrides, halts)."""
        self.log_event(
            event_type="OPERATOR_ACTION",
            description=f"Manual action: {action} | Reason: {reason}",
            severity="CRITICAL",
            actor=actor
        )

    def log_deployment(self, version: str, environment: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log release deployment events."""
        self.log_event(
            event_type="DEPLOYMENT",
            description=f"Application deployed: version={version} env={environment}",
            severity="INFO",
            metadata=metadata
        )
