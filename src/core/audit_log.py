"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/audit_log.py
Full audit trail for compliance and debugging.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import sessionmaker

from src.core.trade_logger import AuditMixin, Base

logger = logging.getLogger(__name__)


class AuditLog(Base, AuditMixin):
    """Full audit trail for compliance and debugging."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    actor = Column(String(50))  # system, operator, ai_model, risk_engine
    action = Column(String(100))
    status = Column(String(20))  # SUCCESS, FAILURE, BLOCKED
    details = Column(Text)  # Human readable summary
    metadata_json = Column(JSON)  # Structured data (decision chain, prediction scores, etc)


class AuditLogger:
    """Enterprise audit logging interface."""

    def __init__(self, engine) -> None:
        self.engine = engine
        # Ensure tables are created
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def _log(
        self,
        event_type: str,
        actor: str,
        action: str,
        status: str,
        details: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Internal helper to write audit log entry."""
        try:
            with self.Session() as session:
                log_entry = AuditLog(
                    event_type=event_type,
                    actor=actor,
                    action=action,
                    status=status,
                    details=details,
                    metadata_json=metadata,
                )
                session.add(log_entry)
                session.commit()
        except Exception as e:
            logger.error("Failed to write audit log: %s", e)

    def log_config_change(self, field: str, old_value: Any, new_value: Any, reason: str) -> None:
        """Log configuration changes affecting trading behavior."""
        self._log(
            event_type="CONFIG_CHANGE",
            actor="operator",
            action=f"Changed {field}",
            status="SUCCESS",
            details=f"Configuration field '{field}' changed from '{old_value}' to '{new_value}'. Reason: {reason}",
            metadata={
                "field": field,
                "old_value": str(old_value),
                "new_value": str(new_value),
                "reason": reason,
            },
        )

    def log_trade_blocked(self, signal_id: Optional[int], reason: str, decision_chain: Dict[str, Any]) -> None:
        """Log why trades were blocked by risk engine."""
        self._log(
            event_type="TRADE_BLOCKED",
            actor="risk_engine",
            action="Block Trade",
            status="BLOCKED",
            details=f"Trade blocked by risk engine. Primary reason: {reason}",
            metadata={
                "signal_id": signal_id,
                "reason": reason,
                "decision_chain": decision_chain,
            },
        )

    def log_model_prediction(
        self,
        symbol: str,
        direction: int,
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log model prediction outcomes and confidence scores."""
        dir_str = "BUY" if direction == 1 else "SELL" if direction == -1 else "HOLD"
        self._log(
            event_type="MODEL_PREDICTION",
            actor="ai_model",
            action="Predict",
            status="SUCCESS",
            details=f"Model predicted {dir_str} for {symbol} with {confidence:.2f} confidence",
            metadata={
                "symbol": symbol,
                "direction": direction,
                "confidence": confidence,
                "additional_info": metadata,
            },
        )

    def log_risk_decision(self, signal_id: Optional[int], passed: bool, decision_chain: Dict[str, Any]) -> None:
        """Log risk engine decision chain (which filters passed/failed)."""
        status = "SUCCESS" if passed else "FAILURE"
        action = "Approve Trade" if passed else "Reject Trade"
        self._log(
            event_type="RISK_DECISION",
            actor="risk_engine",
            action=action,
            status=status,
            details=f"Risk engine {'passed' if passed else 'failed'} the signal validation.",
            metadata={
                "signal_id": signal_id,
                "passed": passed,
                "decision_chain": decision_chain,
            },
        )

    def log_operator_action(self, action: str, details: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log manual overrides, emergency halts, etc."""
        self._log(
            event_type="OPERATOR_ACTION",
            actor="operator",
            action=action,
            status="SUCCESS",
            details=details,
            metadata=metadata,
        )

    def log_deployment_event(self, version: str, environment: str, details: str) -> None:
        """Log release deployment events."""
        self._log(
            event_type="DEPLOYMENT_EVENT",
            actor="release_pipeline",
            action="Deploy",
            status="SUCCESS",
            details=f"Version {version} deployed to {environment}. {details}",
            metadata={"version": version, "environment": environment},
        )
