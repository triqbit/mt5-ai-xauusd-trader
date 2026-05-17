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
        Run the full 8-layer risk filter cascade.
        Returns RiskDecision with approval status and reason.
        Logs the full decision chain to the audit log.
        """
        decision_chain = {
            "circuit_breaker": bool(self._check_circuit_breaker()),
            "daily_loss": bool(self.get_daily_loss_level() < 4),
            "activity_limits": bool(
                self.daily.trade_count < self.cfg.max_trades_per_day
            ),
            "consecutive_losses": bool(
                self.daily.consecutive_losses < self.cfg.max_losing_streak
            ),
            "max_positions": bool(
                len(open_positions) < self.cfg.max_positions
            ),
            "directional_exposure": bool(
                self._check_directional_exposure(signal, open_positions)
            ),
            "total_notional": bool(
                self._check_total_notional(signal, open_positions, market_data)
            ),
            "symbol_allocation": bool(self._check_symbol_allocation(signal.symbol)),
            "min_confidence": bool(signal.confidence >= self.cfg.min_confidence),
            "risk_reward": bool(self._check_risk_reward(signal)),
            "model_health": bool(self._check_model_health(model_health)),
        }

        is_approved = all(decision_chain.values())

        # Calculate lot size if approved
        adjusted_lots = 0.0
        reason = "Approved"

        if is_approved:
            adjusted_lots = float(self.calculate_position_size(signal.symbol, market_data))
            if adjusted_lots < self.cfg.min_lot_size:
                is_approved = False
                reason = f"Calculated lot size {adjusted_lots} below minimum"
        else:
            rejection_reasons = [k for k, v in decision_chain.items() if not v]
            reason = f"Failed filters: {', '.join(rejection_reasons)}"

        # Log to Audit Trail
        try:
            audit = get_audit_logger()
            audit.log_risk_decision(
                symbol=signal.symbol,
                direction=int(signal.direction.value if hasattr(signal.direction, "value") else signal.direction),
                decision_chain={k: bool(v) for k, v in decision_chain.items()},
                passed=bool(is_approved),
            )

            # Log high-severity circuit breaker events specifically
            if not decision_chain.get("circuit_breaker", True):
                audit.log_operator_action(
                    operator="system",
                    action="circuit_breaker_triggered",
                    reason=f"Hard drawdown limit hit during signal validation for {signal.symbol}",
                    metadata={"symbol": signal.symbol, "decision_chain": {k: bool(v) for k, v in decision_chain.items()}},
                )

            if not decision_chain.get("daily_loss", True):
                audit.log_operator_action(
                    operator="system",
                    action="daily_loss_limit_triggered",
                    reason=f"Daily loss limit reached during signal validation for {signal.symbol}",
                    metadata={"symbol": signal.symbol, "decision_chain": {k: bool(v) for k, v in decision_chain.items()}},
                )

        except (RuntimeError, ImportError):
            logger.debug("AuditLogger not available for risk decision logging")

        if not is_approved:
            logger.warning(
                "Signal REJECTED | %s %s | Reason: %s",
                signal.symbol,
                signal.direction,
                reason,
            )
            if self.monitor:
                rejection_reasons = [k for k, v in decision_chain.items() if not v]
                for r in rejection_reasons:
                    self.monitor.record_internal_rejection("risk_manager", r.upper())
            if self.trade_logger:
                self.trade_logger.log_risk_event(
                    event_type="SIGNAL_REJECTED",
                    description=reason,
                    symbol=signal.symbol,
                    signal_id=None,
                )

        return RiskDecision(bool(is_approved), reason, float(adjusted_lots))
