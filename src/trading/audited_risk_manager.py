"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/audited_risk_manager.py
Subclass of RiskManager that adds comprehensive audit logging to the decision chain.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from typing import Optional

from src.core.audit_log import get_audit_logger
from src.core.schemas import TradeSignal
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
        signal_id: Optional[int] = None,
        model_health: Optional[dict] = None,
    ) -> bool:
        """
        Run the full 8-layer risk filter cascade.
        Returns True only if ALL layers pass.
        Logs the full decision chain to the audit log.
        """
        decision_chain = {
            "circuit_breaker": self._check_circuit_breaker(),
            "daily_loss": self._check_daily_loss(),
            "max_positions": self._check_max_positions(),
            "symbol_allocation": self._check_symbol_allocation(signal.symbol),
            "min_confidence": self._check_minimum_confidence(signal.confidence),
            "risk_reward": self._check_risk_reward(signal),
            "consecutive_losses": self._check_consecutive_losses(),
            "model_health": self._check_model_health(model_health),
        }

        passed = all(decision_chain.values())

        # Log to Audit Trail
        try:
            audit = get_audit_logger()
            audit.log_risk_decision(
                symbol=signal.symbol,
                direction=signal.direction,
                decision_chain=decision_chain,
                passed=passed,
            )

            # Log high-severity circuit breaker events specifically
            if not decision_chain.get("circuit_breaker", True):
                audit.log_operator_action(
                    operator="system",
                    action="circuit_breaker_triggered",
                    reason=f"Hard drawdown limit hit during signal validation for {signal.symbol}",
                    metadata={"symbol": signal.symbol, "decision_chain": decision_chain},
                )

            if not decision_chain.get("daily_loss", True):
                audit.log_operator_action(
                    operator="system",
                    action="daily_loss_limit_triggered",
                    reason=f"Daily loss limit reached during signal validation for {signal.symbol}",
                    metadata={"symbol": signal.symbol, "decision_chain": decision_chain},
                )

        except (RuntimeError, ImportError):
            logger.debug("AuditLogger not available for risk decision logging")

        if not passed:
            rejection_reasons = [k for k, v in decision_chain.items() if not v]
            reason_str = ", ".join(rejection_reasons)
            logger.warning(
                "Signal REJECTED | %s %s | Failed: %s",
                signal.symbol,
                signal.direction,
                reason_str,
            )
            if self.monitor:
                for reason in rejection_reasons:
                    self.monitor.record_internal_rejection("risk_manager", reason.upper())
            if self.trade_logger:
                self.trade_logger.log_risk_event(
                    event_type="SIGNAL_REJECTED",
                    description=f"Failed filters: {reason_str}",
                    symbol=signal.symbol,
                    signal_id=signal_id,
                )
        return passed
