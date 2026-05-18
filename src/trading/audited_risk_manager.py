"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/audited_risk_manager.py

Subclass of RiskManager that adds comprehensive audit logging to the decision chain.
Author : triqbit
License: MIT
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
import structlog

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
        decision = super().validate_signal(
            signal, market_data, open_positions, model_health
        )

        # Detailed chain for audit logging
        decision_chain = {
            "circuit_breaker": self._check_circuit_breaker(),
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
            "symbol_allocation": self._check_symbol_allocation(signal.symbol),
            "prediction_limits": self._check_minimum_confidence(signal.confidence),
            "risk_reward": self._check_risk_reward(signal),
            "model_health": self._check_model_health(model_health),
        }

        try:
            audit = get_audit_logger()
            audit.log_risk_decision(
                symbol=signal.symbol,
                direction=signal.direction,
                decision_chain=decision_chain,
                passed=decision.is_approved,
            )

            if not decision.is_approved:
                audit.log_blocked_trade(
                    symbol=signal.symbol,
                    reason=decision.reason,
                    context={
                        "direction": signal.direction,
                        "confidence": signal.confidence,
                        "decision_chain": decision_chain,
                    },
                )
        except Exception:
            logger.debug("AuditLogger not available for risk decision logging")

        if not decision.is_approved:
            if self.monitor:
                self.monitor.record_internal_rejection("risk_manager", decision.reason.upper().replace(" ", "_"))

        return decision

    def approve(
        self,
        signal: TradeSignal,
        signal_id: Optional[int] = None,
        model_health: Optional[dict] = None,
    ) -> bool:
        """
        Legacy support for boolean approval gate with audit logging.
        """
        decision_chain = {
            "circuit_breaker": self._check_circuit_breaker(),
            "daily_loss": self.get_daily_loss_level() < 4,
            "max_positions": len(self.open_positions) < self.cfg.max_positions,
            "symbol_allocation": self._check_symbol_allocation(signal.symbol),
            "min_confidence": self._check_minimum_confidence(signal.confidence),
            "risk_reward": self._check_risk_reward(signal),
            "consecutive_losses": self._check_consecutive_losses(),
            "model_health": self._check_model_health(model_health),
        }

        passed = all(decision_chain.values())

        try:
            audit = get_audit_logger()
            audit.log_risk_decision(
                symbol=signal.symbol,
                direction=signal.direction,
                decision_chain=decision_chain,
                passed=passed,
            )
        except Exception:
            logger.debug("AuditLogger not available for risk decision logging")

        if not passed:
            rejection_reasons = [k for k, v in decision_chain.items() if not v]
            reason_str = ", ".join(rejection_reasons)
            logger.warning(
                "Signal REJECTED",
                symbol=signal.symbol,
                reason=reason_str,
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
