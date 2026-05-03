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
from typing import Any, Dict, Optional

from sqlalchemy import (
    JSON,
    DateTime,
    create_engine,
    String,
    Text,
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
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)


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

    def log(
        self,
        actor: str,
        action: str,
        details: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Record a new audit entry.
        """
        with self.Session() as session:
            entry = AuditEntry(
                actor=actor,
                action=action,
                details=details,
                metadata_json=metadata,
            )
            session.add(entry)
            session.commit()
            return entry.id

    def log_config_change(
        self, old_config: Dict[str, Any], new_config: Dict[str, Any], reason: str
    ) -> int:
        """Log changes in trading parameters."""
        return self.log(
            actor="system",
            action="config_change",
            details=reason,
            metadata={"old": old_config, "new": new_config},
        )

    def log_trade_blocked(
        self, symbol: str, reason: str, decision_chain: Dict[str, Any]
    ) -> int:
        """Detail why a trade was rejected by risk or execution filters."""
        return self.log(
            actor="risk_engine",
            action="trade_blocked",
            details=f"Trade blocked for {symbol}: {reason}",
            metadata={"symbol": symbol, "reason": reason, "decision_chain": decision_chain},
        )

    def log_model_prediction(
        self,
        symbol: str,
        direction: int,
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Record prediction outcomes and confidence."""
        pred_meta = {"symbol": symbol, "direction": direction, "confidence": confidence}
        if metadata:
            pred_meta.update(metadata)
        return self.log(
            actor="ai_model",
            action="prediction",
            details=f"Prediction for {symbol}: dir={direction}, conf={confidence:.4f}",
            metadata=pred_meta,
        )

    def log_risk_decision(
        self, symbol: str, passed: bool, decision_chain: Dict[str, Any]
    ) -> int:
        """Log the full risk engine decision chain."""
        return self.log(
            actor="risk_engine",
            action="risk_decision",
            details=f"Risk decision for {symbol}: {'PASSED' if passed else 'FAILED'}",
            metadata={"symbol": symbol, "passed": passed, "decision_chain": decision_chain},
        )

    def log_operator_action(
        self,
        actor: str,
        action: str,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Track manual overrides or emergency halts."""
        return self.log(actor=actor, action=action, details=reason, metadata=metadata)

    def log_deployment_event(
        self,
        version: str,
        environment: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Record release and deployment details."""
        deploy_meta = {"version": version, "environment": environment, "status": status}
        if metadata:
            deploy_meta.update(metadata)
        return self.log(
            actor="deployer",
            action="deployment",
            details=f"Deployment {version} in {environment}: {status}",
            metadata=deploy_meta,
        )

    @classmethod
    def get_instance(cls) -> AuditLogger:
        """
        Retrieve the singleton instance of the AuditLogger.
        """
        if cls._instance is None or not cls._instance._initialized:
            raise RuntimeError(
                "AuditLogger not initialized. Call AuditLogger(db_url) first."
            )
        return cls._instance


def get_audit_logger() -> AuditLogger:
    """
    Convenience function to retrieve the AuditLogger.
    """
    return AuditLogger.get_instance()
