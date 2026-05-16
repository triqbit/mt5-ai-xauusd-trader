"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/audited_risk_manager.py

Subclass of RiskManager that adds comprehensive audit logging to the decision chain.
Standardized to the 8-layer institutional risk cascade.

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
    Evaluates the full 8-layer decision chain for traceability.
    """

    def validate_signal(
        self,
        signal: TradeSignal,
        market_data: pd.DataFrame,
        open_positions: List[Dict[str, Any]],
        model_health: Optional[Dict[str, float]] = None,
    ) -> RiskDecision:
        """
        Validate signal through the 8-layer cascade and log the decision chain.
        """
        decision_chain = {
            "layer1_drawdown": self._check_circuit_breaker(),
            "layer2_daily_loss": self.get_daily_loss_level() < 4,
            "layer3_activity": self.daily.trade_count < self.cfg.max_trades_per_day
            and self._check_consecutive_losses(),
            "layer4_exposure": len(open_positions) < self.cfg.max_positions
            and self._check_directional_exposure(signal, open_positions)
            and self._check_total_notional(signal, open_positions, market_data),
            "layer5_allocation": self._check_symbol_allocation(signal.symbol),
            "layer6_confidence": self._check_minimum_confidence(signal.confidence),
            "layer7_risk_reward": self._check_risk_reward(signal),
            "layer8_model_health": self._check_model_health(model_health),
        }

        # Run base validation to get final decision (including lot sizing)
        decision = super().validate_signal(
            signal, market_data, open_positions, model_health=model_health
        )

        # Log to Audit Trail
        try:
            audit = get_audit_logger()
            audit.log_risk_decision(
                symbol=signal.symbol,
                direction=signal.direction,
                decision_chain=decision_chain,
                passed=decision.is_approved,
            )

            # High-severity events
            if not decision_chain["layer1_drawdown"]:
                audit.log_operator_action(
                    operator="system",
                    action="circuit_breaker_triggered",
                    reason=f"Hard drawdown limit hit during validation for {signal.symbol}",
                )

            if not decision_chain["layer2_daily_loss"]:
                audit.log_operator_action(
                    operator="system",
                    action="daily_loss_limit_triggered",
                    reason=f"Daily loss limit (Level 4) reached for {signal.symbol}",
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
            if self.monitor:
                self.monitor.record_internal_rejection("risk_manager", decision.reason.upper())
            if self.trade_logger:
                self.trade_logger.log_risk_event(
                    event_type="SIGNAL_REJECTED",
                    description=decision.reason,
                    symbol=signal.symbol,
                )
        return decision

    def approve(
        self,
        signal: TradeSignal,
        signal_id: Optional[int] = None,
        model_health: Optional[dict] = None,
    ) -> bool:
        """
        Legacy 6-layer entry filter cascade wrapper for backward compatibility.
        Deprecated: Use validate_signal instead.
        """
        # We use a dummy market_data and open_positions for legacy compatibility if possible
        # but in most cases this will be called from main.py which we are updating.
        return super().approve(signal, signal_id, model_health)
