"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/audit_log.py
Full audit trail for compliance, debugging, and post-incident review.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import Column, Integer, JSON, String, Text

from src.core.database import AuditMixin, Base

logger = logging.getLogger(__name__)


class AuditLog(Base, AuditMixin):
    """Logs every critical decision and system event."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(50), nullable=False, index=True)
    actor = Column(String(50), default="SYSTEM")
    description = Column(Text, nullable=False)
    details = Column(JSON)  # Stores structured data (config diffs, decision chains, etc.)


class AuditLogger:
    """Utility class for recording audit events."""

    def __init__(self, session_factory: Any) -> None:
        self.Session = session_factory

    def log(
        self,
        event_type: str,
        description: str,
        details: Optional[Dict[str, Any]] = None,
        actor: str = "SYSTEM",
    ) -> None:
        """Create a new audit log entry."""
        try:
            with self.Session() as session:
                entry = AuditLog(
                    event_type=event_type,
                    description=description,
                    details=details,
                    actor=actor,
                )
                session.add(entry)
                session.commit()
                logger.debug("Audit log entry created: %s | %s", event_type, description)
        except Exception as e:
            logger.error("Failed to write audit log: %s", e)

    def log_config_change(self, reason: str, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> None:
        """Log a configuration change with before/after state."""
        self.log(
            event_type="CONFIG_CHANGE",
            description=f"Configuration updated: {reason}",
            details={"old_state": old_config, "new_state": new_config},
        )

    def log_trade_blocked(self, reason: str, signal_details: Dict[str, Any]) -> None:
        """Log why a trade was blocked by the system."""
        self.log(
            event_type="TRADE_BLOCKED",
            description=f"Trade blocked: {reason}",
            details=signal_details,
        )

    def log_model_prediction(self, model_name: str, prediction: int, confidence: float, votes: Dict[str, float]) -> None:
        """Log AI model prediction outcomes."""
        self.log(
            event_type="MODEL_PREDICTION",
            description=f"Model {model_name} predicted {prediction} (conf: {confidence:.2f})",
            details={
                "model": model_name,
                "prediction": prediction,
                "confidence": confidence,
                "votes": votes,
            },
        )

    def log_risk_decision(self, passed: bool, decision_chain: Dict[str, bool], signal_id: Optional[int] = None) -> None:
        """Log the full risk engine decision chain."""
        status = "PASSED" if passed else "FAILED"
        self.log(
            event_type="RISK_DECISION",
            description=f"Risk engine gate {status}",
            details={
                "passed": passed,
                "decision_chain": decision_chain,
                "signal_id": signal_id,
            },
        )

    def log_operator_action(self, action: str, reason: str, actor: str = "OPERATOR") -> None:
        """Log manual interventions or emergency actions."""
        self.log(
            event_type="OPERATOR_ACTION",
            description=f"Operator action: {action} | Reason: {reason}",
            actor=actor,
        )

    def log_deployment(self, version: str, environment: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log deployment events."""
        self.log(
            event_type="DEPLOYMENT",
            description=f"Release deployed: {version} in {environment}",
            details=metadata,
        )
