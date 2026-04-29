"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/audit_log.py
Compliance audit logging system.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import sessionmaker

from src.core.database import AuditMixin, Base

logger = logging.getLogger(__name__)

class AuditLog(Base, AuditMixin):
    """Compliance audit trail for all critical decisions."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=False)
    metadata_json = Column(Text)  # JSON-encoded metadata
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

class AuditLogger:
    """Interface for recording audit events."""

    def __init__(self, db_url: str = "sqlite:///trades.db") -> None:
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def _log(self, event_type: str, description: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        try:
            with self.Session() as session:
                log_entry = AuditLog(
                    event_type=event_type,
                    description=description,
                    metadata_json=json.dumps(metadata) if metadata else None
                )
                session.add(log_entry)
                session.commit()
        except Exception as e:
            logger.error("Failed to write audit log: %s", e)

    def log_config_change(self, reason: str, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> None:
        """Log configuration changes with old and new values."""
        self._log("CONFIG_CHANGE", reason, {"old": old_config, "new": new_config})

    def log_trade_blocked(self, symbol: str, reason: str, filter_results: Dict[str, bool]) -> None:
        """Log why a trade was blocked by the risk engine."""
        self._log("TRADE_BLOCKED", f"Trade for {symbol} blocked: {reason}", {
            "symbol": symbol,
            "reason": reason,
            "filters": filter_results
        })

    def log_model_prediction(self, symbol: str, outcome: int, confidence: float, votes: Dict[str, float]) -> None:
        """Log model prediction details and per-algorithm votes."""
        self._log("MODEL_PREDICTION", f"Model prediction for {symbol}", {
            "symbol": symbol,
            "outcome": outcome,
            "confidence": confidence,
            "votes": votes
        })

    def log_risk_decision(self, symbol: str, passed: bool, chain: Dict[str, Any]) -> None:
        """Log the complete risk engine decision chain."""
        status = "PASSED" if passed else "FAILED"
        self._log("RISK_DECISION", f"Risk engine decision for {symbol}: {status}", {
            "symbol": symbol,
            "passed": passed,
            "chain": chain
        })

    def log_operator_action(self, action: str, reason: str, actor: str = "operator") -> None:
        """Log manual interventions and emergency stops."""
        self._log("OPERATOR_ACTION", f"Action: {action} by {actor}", {
            "action": action,
            "reason": reason,
            "actor": actor
        })

    def _redact_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Deeply redact sensitive keys in configuration dictionaries."""
        redacted = config.copy()
        sensitive_keywords = ["KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL"]
        for k, v in redacted.items():
            if any(kw in k.upper() for kw in sensitive_keywords):
                redacted[k] = "********"
            elif isinstance(v, dict):
                redacted[k] = self._redact_config(v)
        return redacted

    def log_deployment(self, version: str, environment: str, config_snapshot: Dict[str, Any]) -> None:
        """Log software deployment and startup events."""
        redacted_config = self._redact_config(config_snapshot)
        self._log("DEPLOYMENT", f"Deployment of version {version} in {environment}", {
            "version": version,
            "environment": environment,
            "config": redacted_config
        })
