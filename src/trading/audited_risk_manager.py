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
        # We manually run checks to build the decision chain for the audit log
        decision_chain = {
            "drawdown_breaker": self._check_drawdown_breaker(),
            "daily_loss": self.get_daily_loss_level() < 4,
            "activity_limits": self.daily.trade_count < self.cfg.max_trades_per_day
            and self.daily.consecutive_losses < self.cfg.max_losing_streak,
            "exposure_limits": len(open_positions) < self.cfg.max_positions
            and self._check_directional_exposure(signal, open_positions)
            and self._check_total_notional(signal, open_positions, market_data),
            "symbol_allocation": self._check_symbol_allocation(signal.symbol),
            "min_confidence": self._check_minimum_confidence(signal.confidence),
            "risk_reward": self._check_risk_reward(signal),
            "model_health": self._check_model_health(model_health),
        }

        passed = all(decision_chain.values())
        reason = ""
        adjusted_lots = 0.0

        if passed:
            adjusted_lots = self.size_position(signal.symbol, market_data)
            if adjusted_lots < self.cfg.min_lot_size:
                passed = False
                reason = f"Calculated lot size {adjusted_lots} below minimum"
            else:
                reason = "Approved"
        else:
            rejection_reasons = [k for k, v in decision_chain.items() if not v]
            reason = f"Failed filters: {', '.join(rejection_reasons)}"

        # Log to Audit Trail
        try:
            audit = get_audit_logger()
            audit.log_risk_decision(
                symbol=signal.symbol,
                direction=signal.direction.value if hasattr(signal.direction, "value") else signal.direction,
                decision_chain=decision_chain,
                passed=passed,
            )

            # Log high-severity events
            if not decision_chain.get("drawdown_breaker", True):
                audit.log_operator_action(
                    operator="system",
                    action="circuit_breaker_triggered",
                    reason=f"Hard drawdown limit hit during validation for {signal.symbol}",
                    metadata={"symbol": signal.symbol, "decision_chain": decision_chain},
                )

        except (RuntimeError, ImportError):
            logger.debug("AuditLogger not available for risk decision logging")

        if not passed:
            logger.warning(
                "Signal REJECTED | %s %s | %s",
                signal.symbol,
                signal.direction,
                reason,
            )
            if self.monitor:
                failed_keys = [k for k, v in decision_chain.items() if not v]
                for k in failed_keys:
                    self.monitor.record_internal_rejection("risk_manager", k.upper())
            if self.trade_logger:
                self.trade_logger.log_risk_event(
                    event_type="SIGNAL_REJECTED",
                    description=reason,
                    symbol=signal.symbol,
                )

        return RiskDecision(
            is_approved=passed, reason=reason, adjusted_lot_size=adjusted_lots if passed else 0.0
        )
