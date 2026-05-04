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

    def log(self, actor: str, action: str, details: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> int:
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

    def log_config_snapshot(self, config_dict: Dict[str, Any], reason: str) -> int:
        """Log a full configuration snapshot."""
        return self.log(
            actor="system",
            action="config_snapshot",
            details=f"Reason: {reason}",
            metadata=config_dict
        )

    def log_blocked_trade(self, symbol: str, reason: str, details: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> int:
        """Log why a trade was blocked."""
        meta = metadata or {}
        meta["reason"] = reason
        return self.log(
            actor="execution_filter",
            action="trade_blocked",
            details=f"Symbol: {symbol} | Reason: {reason} | {details or ''}",
            metadata=meta
        )

    def log_prediction(self, symbol: str, direction: int, confidence: float, model_name: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """Log model prediction outcomes and confidence scores."""
        meta = metadata or {}
        meta.update({
            "symbol": symbol,
            "direction": direction,
            "confidence": confidence,
            "model_name": model_name
        })
        return self.log(
            actor="model",
            action="prediction_generated",
            details=f"Symbol: {symbol} | Dir: {direction} | Conf: {confidence:.4f} | Model: {model_name}",
            metadata=meta
        )

    def log_risk_decision(self, symbol: str, passed: bool, decision_chain: Dict[str, Any], signal_id: Optional[int] = None) -> int:
        """Log risk engine decision chain (which filters passed/failed)."""
        return self.log(
            actor="risk_manager",
            action="risk_decision",
            details=f"Symbol: {symbol} | Passed: {passed} | SignalID: {signal_id}",
            metadata={
                "symbol": symbol,
                "passed": passed,
                "decision_chain": decision_chain,
                "signal_id": signal_id
            }
        )

    def log_operator_action(self, actor: str, action: str, details: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> int:
        """Log operator actions (manual overrides, emergency halts)."""
        return self.log(
            actor=actor,
            action=action,
            details=details,
            metadata=metadata
        )

    def log_deployment(self, version: str, environment: str, status: str = "success") -> int:
        """Log release deployment events."""
        return self.log(
            actor="deploy_pipeline",
            action="release_deployment",
            details=f"Version: {version} | Env: {environment} | Status: {status}",
            metadata={
                "version": version,
                "environment": environment,
                "status": status
            }
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
