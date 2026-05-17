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
        Run the full 8-layer risk filter cascade and log the result.
        """
        # We perform individual checks to build the decision chain for the audit log
        decision_chain = {
            "circuit_breaker": self._check_circuit_breaker(),
            "daily_loss": self.get_daily_loss_level() < 4,
            "max_trades": self.daily.trade_count < self.cfg.max_trades_per_day,
            "consecutive_losses": self.daily.consecutive_losses < self.cfg.max_losing_streak,
            "max_positions": len(open_positions) < self.cfg.max_positions,
            "directional_exposure": self._check_directional_exposure(signal, open_positions),
            "total_notional": self._check_total_notional(signal, open_positions, market_data),
            "symbol_allocation": self._check_symbol_allocation(signal.symbol),
            "min_confidence": signal.confidence >= self.cfg.min_confidence,
            "risk_reward": self._check_risk_reward(signal),
            "model_health": self._check_model_health(model_health),
        }

        passed = all(decision_chain.values())

        # Calculate lot size if passed
        lots = 0.0
        if passed:
            lots = self.size_position(signal.symbol, market_data)
            if lots < self.cfg.min_lot_size:
                passed = False
                decision_chain["lot_sizing"] = False
                reason = f"Calculated lot size {lots} below minimum"
            else:
                decision_chain["lot_sizing"] = True
                reason = "Approved"
        else:
            failed_layers = [k for k, v in decision_chain.items() if not v]
            reason = f"Rejected by: {', '.join(failed_layers)}"

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
                failed_layers = [k for k, v in decision_chain.items() if not v]
                for layer in failed_layers:
                    self.monitor.record_internal_rejection("risk_manager", layer.upper())

        return RiskDecision(is_approved=passed, reason=reason, adjusted_lot_size=lots)

    def approve(
        self,
        signal: TradeSignal,
        signal_id: Optional[int] = None,
        model_health: Optional[dict] = None,
    ) -> bool:
        """
        Legacy approval gate.
        """
        decision = self.validate_signal(signal, pd.DataFrame(), [], model_health)
        if not decision.is_approved and self.trade_logger:
            self.trade_logger.log_risk_event(
                event_type="SIGNAL_REJECTED",
                description=decision.reason,
                symbol=signal.symbol,
                signal_id=signal_id,
            )
        return decision.is_approved
