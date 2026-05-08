"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/audit_log.py
Enterprise audit logging system for production traceability.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import (
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, sessionmaker

from src.core.log_config import get_masking_processor
from src.core.database import Base, AuditMixin, create_resilient_engine, with_db_retry

logger = logging.getLogger(__name__)


class AuditEntry(Base, AuditMixin):
    """
    Audit log entry for recording system actions and events.
    Aligned with enterprise traceability requirements.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String(100), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class AuditLogger:
    """
    Singleton AuditLogger for managing system audit traces with resilient DB handling.
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

        self.engine = create_resilient_engine(db_url)
        # In production, we favor Alembic migrations, but for ease of use/testing:
        if "sqlite" in db_url:
            Base.metadata.create_all(self.engine)

        self.Session = sessionmaker(bind=self.engine)
        self._initialized = True
        logger.info("AuditLogger initialized with resilient engine: %s", db_url.split('@')[-1] if '@' in db_url else db_url)

    @with_db_retry()
    def log(
        self,
        actor: str,
        action: str,
        details: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """
        Record a new audit entry.
        """
        # Redact metadata before persisting to database
        redacted_metadata = None
        if metadata:
            redacted_metadata = get_masking_processor().redact_any(metadata)

        with self.Session() as session:
            entry = AuditEntry(
                actor=actor,
                action=action,
                details=details,
                metadata_json=redacted_metadata,
            )
            session.add(entry)
            session.commit()
            return entry.id

    def log_config_snapshot(self, config_data: dict[str, Any], reason: str = "startup") -> int:
        """Log a snapshot of the system configuration."""
        return self.log(
            actor="system",
            action="config_snapshot",
            details=f"Configuration snapshot: {reason}",
            metadata=config_data,
        )

    def log_prediction(
        self,
        symbol: str,
        direction: int,
        confidence: float,
        model_metadata: dict[str, Any] | None = None,
    ) -> int:
        """Log a model prediction and its confidence."""
        return self.log(
            actor="model",
            action="prediction",
            details=f"Prediction for {symbol}: {direction} (conf: {confidence:.4f})",
            metadata={
                "symbol": symbol,
                "direction": direction,
                "confidence": confidence,
                "model_context": model_metadata,
            },
        )

    def log_risk_decision(
        self, symbol: str, direction: int, decision_chain: dict[str, Any], passed: bool
    ) -> int:
        """Log the full risk engine decision chain."""
        return self.log(
            actor="risk_engine",
            action="risk_decision",
            details=f"Risk decision for {symbol} {direction}: {'PASSED' if passed else 'FAILED'}",
            metadata={
                "symbol": symbol,
                "direction": direction,
                "decision_chain": decision_chain,
                "passed": passed,
            },
        )

    def log_execution_decision(
        self,
        symbol: str,
        direction: int,
        trace: dict[str, Any],
        is_approved: bool,
    ) -> int:
        """
        Log the technical execution filter decision and its full trace.
        """
        return self.log(
            actor="execution_filter",
            action="execution_decision",
            details=f"Execution decision for {symbol} {direction}: {'PASSED' if is_approved else 'FAILED'}",
            metadata={
                "symbol": symbol,
                "direction": direction,
                "trace": trace,
                "is_approved": is_approved,
            },
        )

    def log_blocked_trade(
        self, symbol: str, reason: str, context: dict[str, Any] | None = None
    ) -> int:
        """Log when a trade is blocked by filters or risk management."""
        return self.log(
            actor="system",
            action="trade_blocked",
            details=f"Trade blocked for {symbol}: {reason}",
            metadata={"symbol": symbol, "reason": reason, "context": context},
        )

    def log_operator_action(
        self, operator: str, action: str, reason: str, metadata: dict[str, Any] | None = None
    ) -> int:
        """Log manual operator actions like emergency halts."""
        combined_metadata = {"action_type": action, "reason": reason}
        if metadata:
            combined_metadata.update(metadata)

        return self.log(
            actor=operator,
            action=f"operator_{action}",
            details=f"Operator action: {action}. Reason: {reason}",
            metadata=combined_metadata,
        )

    def log_deployment(self, version: str, environment: str, status: str = "success") -> int:
        """Log a deployment event."""
        return self.log(
            actor="system",
            action="deployment",
            details=f"Deployment {version} to {environment}: {status}",
            metadata={"version": version, "environment": environment, "status": status},
        )

    def log_trade_outcome(
        self,
        ticket: int,
        symbol: str,
        pnl: float,
        reason: str = "close",
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Log the final outcome of a trade."""
        return self.log(
            actor="system",
            action="trade_outcome",
            details=f"Trade {ticket} ({symbol}) closed with PnL: {pnl:.2f}. Reason: {reason}",
            metadata={
                "ticket": ticket,
                "symbol": symbol,
                "pnl": pnl,
                "reason": reason,
                "context": metadata,
            },
        )

    def log_config_change(
        self, old_config: dict[str, Any], new_config: dict[str, Any], reason: str
    ) -> int:
        """Log changes to system configuration."""
        return self.log(
            actor="system",
            action="config_change",
            details=f"Configuration changed: {reason}",
            metadata={
                "old": old_config,
                "new": new_config,
                "reason": reason,
            },
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
