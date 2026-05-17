"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/audited_risk_manager.py
Subclass of RiskManager that adds comprehensive audit logging to the decision chain.
Author : triqbit, Jules05
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
        Run the full 8-layer risk filter cascade and log the decision.
        """
        decision = super().validate_signal(signal, market_data, open_positions, model_health)

        # Log to Audit Trail
        try:
            audit = get_audit_logger()
            # Construct a decision chain for logging
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

            audit.log_risk_decision(
                symbol=signal.symbol,
                direction=signal.direction,
                decision_chain=decision_chain,
                passed=decision.is_approved,
            )

            if not decision.is_approved:
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

        except (RuntimeError, ImportError, AttributeError):
            logger.debug("AuditLogger not available for risk decision logging")

        if not decision.is_approved:
            logger.warning(
                "Signal REJECTED | %s %s | Reason: %s",
                signal.symbol,
                signal.direction,
                decision.reason,
            )
            if self.monitor:
                self.monitor.record_internal_rejection(
                    "risk_manager", decision.reason.upper().replace(" ", "_")
                )
            if self.trade_logger:
                self.trade_logger.log_risk_event(
                    event_type="SIGNAL_REJECTED",
                    description=decision.reason,
                    symbol=signal.symbol,
                )

        return decision

    def approve(self, signal: TradeSignal, **kwargs) -> bool:
        """Legacy boolean gate for backward compatibility."""
        decision = self.validate_signal(signal, pd.DataFrame(), [], **kwargs)
        return decision.is_approved
