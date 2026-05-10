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
        market_data: Optional[pd.DataFrame] = None,
        open_positions: Optional[List[Dict[str, Any]]] = None,
        model_health: Optional[Dict[str, float]] = None,
        signal_id: Optional[int] = None,
    ) -> RiskDecision:
        """
        Run the full 8-layer risk filter cascade.
        Logs the full decision chain to the audit log.
        """
        decision = super().approve(
            signal=signal,
            market_data=market_data,
            open_positions=open_positions,
            model_health=model_health,
            signal_id=signal_id,
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
            if not decision.is_approved:
                if not decision.trace.get("circuit_breaker", {}).get("passed", True):
                    audit.log_operator_action(
                        operator="system",
                        action="circuit_breaker_triggered",
                        reason=f"Hard drawdown limit hit during signal validation for {signal.symbol}",
                        metadata={"symbol": signal.symbol, "trace": decision.trace},
                    )

                if not decision.trace.get("daily_loss", {}).get("passed", True):
                    audit.log_operator_action(
                        operator="system",
                        action="daily_loss_limit_triggered",
                        reason=f"Daily loss limit reached during signal validation for {signal.symbol}",
                        metadata={"symbol": signal.symbol, "trace": decision.trace},
                    )

        except (RuntimeError, ImportError):
            logger.debug("AuditLogger not available for risk decision logging")

        if not decision.is_approved:
            logger.warning(
                "Signal REJECTED | %s %s | Reason: %s",
                signal.symbol,
                signal.direction,
                decision.reason,
            )
            if self.trade_logger:
                self.trade_logger.log_risk_event(
                    event_type="SIGNAL_REJECTED",
                    description=decision.reason,
                    symbol=signal.symbol,
                    signal_id=signal_id,
                )
        return decision
