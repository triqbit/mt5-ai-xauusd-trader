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
from src.core.schemas import TradeSignal
from src.trading.risk_manager import RiskDecision, RiskManager

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
        decision_chain = {
            "circuit_breaker": self._check_drawdown_breaker(),
            "daily_loss": self.get_daily_loss_level() < 4,
            "activity_limits": (
                self.daily.trade_count < self.cfg.max_trades_per_day
                and self.daily.consecutive_losses < self.cfg.max_losing_streak
            ),
            "exposure_limits": (
                len(open_positions) < self.cfg.max_positions
                and self._check_directional_exposure(signal, open_positions)
                and self._check_total_notional(signal, open_positions, market_data)
            ),
            "symbol_allocation": signal.symbol == self.cfg.symbol,
            "prediction_limits": signal.confidence >= self.cfg.min_confidence,
            "risk_reward": self._check_risk_reward(signal),
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

            if not decision_chain.get("circuit_breaker", True):
                audit.log_operator_action(
                    operator="system",
                    action="circuit_breaker_triggered",
                    reason=f"Hard drawdown limit hit during validation for {signal.symbol}",
                    metadata={"symbol": signal.symbol, "decision_chain": decision_chain},
                )
        except (RuntimeError, ImportError):
            logger.debug("AuditLogger not available")

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
            return RiskDecision(False, f"Failed filters: {reason_str}")

        # If passed, calculate lot size
        adjusted_lots = self.calculate_position_size(signal.symbol, market_data)

        if adjusted_lots < self.cfg.min_lot_size:
            return RiskDecision(False, f"Calculated lot size {adjusted_lots} below minimum")

        return RiskDecision(True, "Approved", adjusted_lots)

    def approve(
        self,
        signal: TradeSignal,
        signal_id: Optional[int] = None,
        model_health: Optional[dict] = None,
    ) -> bool:
        """
        Legacy compatibility wrapper for approve().
        Note: This lacks market_data and open_positions, so it's less accurate.
        Use validate_signal() instead.
        """
        logger.warning("AuditedRiskManager.approve() is legacy. Use validate_signal() instead.")
        # Minimal shim
        decision = self.validate_signal(signal, pd.DataFrame(), [], model_health)
        return decision.is_approved
