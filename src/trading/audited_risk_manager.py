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
        signal_id: Optional[int] = None,
    ) -> RiskDecision:
        """
        Validate a trade signal against the 8-layer cascade and log the full
        decision chain to the audit trail.
        """
        decision_chain = {
            "circuit_breaker": self._check_circuit_breaker(),
            "daily_loss": self._check_daily_loss(),
            "activity_limits": self._check_consecutive_losses()
            and (self.daily.trade_count < self.cfg.max_trades_per_day),
            "exposure_limits": len(open_positions) < self.cfg.max_positions
            and self._check_directional_exposure(signal, open_positions)
            and self._check_total_notional(signal, open_positions, market_data),
            "symbol_allocation": self._check_symbol_allocation(signal.symbol),
            "min_confidence": self._check_minimum_confidence(signal.confidence),
            "risk_reward": self._check_risk_reward(signal),
            "model_health": self._check_model_health(model_health),
        }

        passed = all(decision_chain.values())

        # Calculate lot size if passed basic gates
        adjusted_lots = 0.0
        if passed:
            adjusted_lots = self.calculate_position_size(signal.symbol, market_data)
            if adjusted_lots < self.cfg.min_lot_size:
                passed = False
                decision_chain["lot_sizing"] = False
            else:
                decision_chain["lot_sizing"] = True

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
            rejection_reasons = [k for k, v in decision_chain.items() if not v]
            reason_str = ", ".join(rejection_reasons)
            self._reject(f"Failed filters: {reason_str}", signal, signal_id)
            if self.monitor:
                for reason in rejection_reasons:
                    self.monitor.record_internal_rejection("risk_manager", reason.upper())
            return RiskDecision(False, reason_str)

        return RiskDecision(True, "Approved", adjusted_lots)

    def approve(
        self,
        signal: TradeSignal,
        signal_id: Optional[int] = None,
        model_health: Optional[dict] = None,
    ) -> bool:
        """
        Legacy entry point with audit logging.
        """
        decision_chain = {
            "circuit_breaker": self._check_circuit_breaker(),
            "daily_loss": self._check_daily_loss(),
            "max_positions": self._check_max_positions_legacy(),
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
        except (RuntimeError, ImportError):
            logger.debug("AuditLogger not available for risk decision logging")

        if not passed:
            rejection_reasons = [k for k, v in decision_chain.items() if not v]
            reason_str = ", ".join(rejection_reasons)
            self._reject(f"Failed legacy filters: {reason_str}", signal, signal_id)
            if self.monitor:
                for reason in rejection_reasons:
                    self.monitor.record_internal_rejection("risk_manager", reason.upper())

        return passed
