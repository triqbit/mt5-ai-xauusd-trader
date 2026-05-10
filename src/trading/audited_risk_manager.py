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

    def approve(
        self,
        signal: TradeSignal,
        signal_id: Optional[int] = None,
        model_health: Optional[dict] = None,
        market_data: Optional[pd.DataFrame] = None,
        open_positions: Optional[List[Dict[str, Any]]] = None,
    ) -> RiskDecision:
        """
        Run the full 8-layer risk filter cascade.
        Returns RiskDecision only if ALL layers pass.
        Logs the full decision chain to the audit log.
        """
        positions = open_positions if open_positions is not None else []

        decision_chain = {
            "circuit_breaker": self._check_circuit_breaker(),
            "daily_loss": self.get_daily_loss_level() < 4,
            "max_positions": len(positions) < self.cfg.max_positions,
            "symbol_allocation": self._check_symbol_allocation(signal.symbol),
            "min_confidence": self._check_minimum_confidence(signal.confidence),
            "risk_reward": self._check_risk_reward(signal),
            "consecutive_losses": self._check_consecutive_losses(),
            "model_health": self._check_model_health(model_health),
            "directional_exposure": self._check_directional_exposure(signal, positions),
        }

        if market_data is not None:
            decision_chain["total_notional"] = self._check_total_notional(signal, positions, market_data)

        is_approved = all(decision_chain.values())

        # Calculate final lot size
        adjusted_lots = signal.lot_size
        if is_approved and market_data is not None:
            adjusted_lots = self.calculate_position_size(signal.symbol, market_data)

        if is_approved and adjusted_lots < self.cfg.min_lot_size:
            is_approved = False
            decision_chain["min_lot_size"] = False
            reason = f"Calculated lot size {adjusted_lots} below minimum"
        elif not is_approved:
            rejection_reasons = [k for k, v in decision_chain.items() if not v]
            reason = f"Failed filters: {', '.join(rejection_reasons)}"
        else:
            reason = "Approved"

        # Log to Audit Trail
        try:
            audit = get_audit_logger()
            audit.log_risk_decision(
                symbol=signal.symbol,
                direction=signal.direction,
                decision_chain=decision_chain,
                passed=is_approved,
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

        if not is_approved:
            logger.warning(
                "Signal REJECTED | %s %s | %s",
                signal.symbol,
                signal.direction,
                reason,
            )
            if self.trade_logger:
                self.trade_logger.log_risk_event(
                    event_type="SIGNAL_REJECTED",
                    description=reason,
                    symbol=signal.symbol,
                    signal_id=signal_id,
                )

        return RiskDecision(is_approved=is_approved, reason=reason, adjusted_lot_size=adjusted_lots)
