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
        Validate a trade signal and log the full decision chain to the audit log.
        """
        decision_chain = {
            "circuit_breaker": self._check_drawdown_breaker(),
            "daily_loss": self.get_daily_loss_level() < 4,
            "max_trades": self.daily.trade_count < self.cfg.max_trades_per_day,
            "max_positions": len(open_positions) < self.cfg.max_positions,
            "directional_exposure": self._check_directional_exposure(signal, open_positions),
            "total_notional": self._check_total_notional(signal, open_positions, market_data),
            "symbol_allocation": self._check_symbol_allocation(signal.symbol),
            "min_confidence": self._check_minimum_confidence(signal.confidence),
            "risk_reward": self._check_risk_reward(signal),
            "consecutive_losses": self._check_consecutive_losses(),
            "model_health": self._check_model_health(model_health),
        }

        passed = all(decision_chain.values())
        adjusted_lots = 0.0
        reason = "Approved"

        if passed:
            adjusted_lots = self.size_position(signal.symbol, market_data=market_data)
            if adjusted_lots < self.cfg.min_lot_size:
                passed = False
                reason = f"Calculated lot size {adjusted_lots} below minimum"
                decision_chain["lot_size"] = False
        else:
            rejection_reasons = [k for k, v in decision_chain.items() if not v]
            reason = f"Failed filters: {', '.join(rejection_reasons)}"

        self._log_audit(signal, decision_chain, passed)

        if not passed:
            logger.warning(
                "Signal REJECTED | %s %s | %s",
                signal.symbol,
                signal.direction,
                reason,
            )
            if self.monitor:
                rejection_reasons = [k for k, v in decision_chain.items() if not v]
                for r in rejection_reasons:
                    self.monitor.record_internal_rejection("risk_manager", r.upper())

        return RiskDecision(is_approved=passed, reason=reason, adjusted_lot_size=adjusted_lots)

    def approve(
        self,
        signal: TradeSignal,
        signal_id: Optional[int] = None,
        model_health: Optional[dict] = None,
    ) -> bool:
        """
        Legacy compatibility wrapper for validate_signal with audit logging.
        """
        decision_chain = {
            "circuit_breaker": self._check_drawdown_breaker(),
            "daily_loss": self.get_daily_loss_level() < 4,
            "max_positions": len(self.open_positions) < self.cfg.max_positions,
            "symbol_allocation": self._check_symbol_allocation(signal.symbol),
            "min_confidence": self._check_minimum_confidence(signal.confidence),
            "risk_reward": self._check_risk_reward(signal),
            "consecutive_losses": self._check_consecutive_losses(),
            "model_health": self._check_model_health(model_health),
        }

        passed = all(decision_chain.values())

        self._log_audit(signal, decision_chain, passed)

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

    def _log_audit(self, signal: TradeSignal, decision_chain: Dict[str, bool], passed: bool) -> None:
        """Common audit logging logic."""
        try:
            audit = get_audit_logger()
            audit.log_risk_decision(
                symbol=signal.symbol,
                direction=signal.direction.value,
                decision_chain=decision_chain,
                passed=passed,
            )
        except (RuntimeError, ImportError):
            logger.debug("AuditLogger not available for risk decision logging")
