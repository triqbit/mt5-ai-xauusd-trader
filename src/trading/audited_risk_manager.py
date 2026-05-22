"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/audited_risk_manager.py
Subclass of RiskManager that adds comprehensive audit logging to the decision chain.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import structlog
from typing import Any, Dict, List, Optional

import pandas as pd

from src.core.audit_log import get_audit_logger
from src.core.schemas import TradeSignal
from src.trading.risk_manager import RiskDecision, RiskManager

logger = structlog.get_logger(__name__)


class AuditedRiskManager(RiskManager):
    """
    Enterprise Risk Manager with integrated audit logging.
    Evaluates the full decision chain for traceability.
    """

    def validate_signal(
        self,
        signal: TradeSignal,
        market_data: pd.DataFrame,
        open_positions: List[Dict[str, Any]],
        model_health: Optional[Dict[str, float]] = None,
    ) -> RiskDecision:
        """
        Run the full 8-layer risk filter cascade with audit logging.
        """
        decision = super().validate_signal(signal, market_data, open_positions, model_health)

        # Log to Audit Trail
        try:
            audit = get_audit_logger()
            audit.log_risk_decision(
                symbol=signal.symbol,
                direction=signal.direction,
                decision_chain={
                    "is_approved": decision.is_approved,
                    "reason": decision.reason,
                    "lots": decision.adjusted_lot_size,
                },
                passed=decision.is_approved,
            )

            if not decision.is_approved:
                # Log high-severity triggers
                if "drawdown" in decision.reason.lower():
                    audit.log_operator_action(
                        operator="system",
                        action="circuit_breaker_triggered",
                        reason=f"Hard drawdown limit hit during validation for {signal.symbol}",
                        metadata={"symbol": signal.symbol, "reason": decision.reason},
                    )
                elif "daily loss" in decision.reason.lower():
                    audit.log_operator_action(
                        operator="system",
                        action="daily_loss_limit_triggered",
                        reason=f"Daily loss limit reached during validation for {signal.symbol}",
                        metadata={"symbol": signal.symbol, "reason": decision.reason},
                    )
        except (RuntimeError, ImportError):
            logger.debug("AuditLogger not available for risk decision logging")

        if not decision.is_approved:
            if self.monitor:
                self.monitor.record_internal_rejection("risk_manager", decision.reason.upper())

        return decision

    def approve(
        self,
        signal: TradeSignal,
        signal_id: Optional[int] = None,
        model_health: Optional[dict] = None,
    ) -> bool:
        """
        Legacy entry point for backward compatibility with auditing.
        """
        passed = super().approve(signal, signal_id, model_health)

        # Log to Audit Trail
        try:
            audit = get_audit_logger()
            audit.log_risk_decision(
                symbol=signal.symbol,
                direction=signal.direction,
                decision_chain={"passed": passed},
                passed=passed,
            )
        except (RuntimeError, ImportError):
            logger.debug("AuditLogger not available for risk decision logging")

        return passed
