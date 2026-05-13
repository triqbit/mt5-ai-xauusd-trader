"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/audited_risk_manager.py
Subclass of RiskManager that adds comprehensive audit logging to the decision chain.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from src.core.audit_log import get_audit_logger
from src.core.schemas import RiskDecision, TradeSignal
from src.trading.risk_manager import RiskManager

logger = logging.getLogger(__name__)


class AuditedRiskManager(RiskManager):
    """
    Enterprise Risk Manager with integrated audit logging.
    Evaluates the full decision chain for traceability.
    """

    def approve(
        self,
        signal: TradeSignal,
        market_data: pd.DataFrame,
        open_positions: List[Dict[str, Any]],
        signal_id: Optional[int] = None,
        model_health: Optional[dict] = None,
    ) -> RiskDecision:
        """
        Run the full 8-layer risk filter cascade.
        Returns RiskDecision and logs the full chain to the audit log.
        """
        # Call the base manager's approve method which now returns a RiskDecision
        decision = super().approve(
            signal=signal,
            market_data=market_data,
            open_positions=open_positions,
            signal_id=signal_id,
            model_health=model_health,
        )

        # Log to Audit Trail
        try:
            audit = get_audit_logger()
            audit.log_risk_decision(
                symbol=signal.symbol,
                direction=signal.direction,
                decision_chain=decision.trace,
                passed=decision.is_approved,
            )

            # Log high-severity circuit breaker events specifically
            if not decision.trace.get("circuit_breaker", True):
                audit.log_operator_action(
                    operator="system",
                    action="circuit_breaker_triggered",
                    reason=f"Hard drawdown limit hit during signal validation for {signal.symbol}",
                    metadata={"symbol": signal.symbol, "decision_chain": decision.trace},
                )

            if not decision.trace.get("daily_loss", True):
                audit.log_operator_action(
                    operator="system",
                    action="daily_loss_limit_triggered",
                    reason=f"Daily loss limit reached during signal validation for {signal.symbol}",
                    metadata={"symbol": signal.symbol, "decision_chain": decision.trace},
                )

        except (RuntimeError, ImportError):
            logger.debug("AuditLogger not available for risk decision logging")

        if not decision.is_approved:
            if self.monitor:
                rejection_reasons = [k for k, v in decision.trace.items() if not v]
                for reason in rejection_reasons:
                    self.monitor.record_internal_rejection("risk_manager", reason.upper())

        return decision
