"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/audit_log.py
Enterprise audit logging system for production traceability.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import json
from typing import Any

from sqlalchemy import (
    DateTime,
    JSON,
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
        DateTime, default=lambda: datetime.now(UTC), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    actor: Mapped[str] = mapped_column(String(100), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class AuditLogger:
    """
    Singleton AuditLogger for managing system audit traces.
    """
    _instance: AuditLogger | None = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_url: str | None = None) -> None:
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
        details: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """
        Record a new audit entry with optional structured metadata.
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

    def log_config_snapshot(self, config_dict: dict[str, Any]) -> int:
        """Record a sanitized snapshot of the runtime configuration."""
        return self.log(
            actor="system",
            action="config_snapshot",
            details="Runtime configuration snapshot captured at startup.",
            metadata=config_dict,
        )

    def log_blocked_trade(self, signal_id: int, reasons: list[str], context: dict[str, Any]) -> int:
        """Record a signal that was blocked by the execution filter or risk layers."""
        return self.log(
            actor="risk_manager",
            action="trade_blocked",
            details=f"Signal {signal_id} blocked. Reasons: {', '.join(reasons)}",
            metadata={"signal_id": signal_id, "reasons": reasons, "context": context},
        )

    def log_prediction(
        self, symbol: str, direction: int, confidence: float, metadata: dict[str, Any]
    ) -> int:
        """Record a raw prediction from the AI models."""
        return self.log(
            actor="model",
            action="prediction_generated",
            details=f"Prediction for {symbol}: dir={direction}, conf={confidence:.2f}",
            metadata={
                "symbol": symbol,
                "direction": direction,
                "confidence": confidence,
                **metadata,
            },
        )

    def log_risk_decision(self, signal_id: int, decision: bool, context: dict[str, Any]) -> int:
        """Record a final risk approval/rejection decision with full context."""
        status = "APPROVED" if decision else "REJECTED"
        return self.log(
            actor="risk_manager",
            action="risk_decision",
            details=f"Signal {signal_id} risk check: {status}",
            metadata={"signal_id": signal_id, "decision": decision, "context": context},
        )

    def log_operator_action(self, actor: str, action: str, details: str) -> int:
        """Record an explicit action taken by a human operator or automated guardian."""
        return self.log(actor=actor, action=action, details=details)

    def log_deployment(self, version: str, environment: str) -> int:
        """Record a deployment event."""
        return self.log(
            actor="deploy_pipeline",
            action="deployment_started",
            details=f"Deploying version {version} to {environment}",
            metadata={"version": version, "environment": environment},
        )

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
