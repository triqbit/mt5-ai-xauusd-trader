"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/audited_risk_manager.py
Subclass of RiskManager that adds comprehensive audit logging to the decision chain.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from typing import Optional

from src.core.audit_log import get_audit_logger
from src.core.schemas import TradeSignal
from src.trading.risk_manager import RiskManager

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
    ) -> bool:
        """
        Run the full 8-layer risk filter cascade.
        Returns True only if ALL layers pass.
        Logs the full decision chain with metrics to the audit log.
        """
        # Gather metrics for the audit trail
        drawdown = (self.peak_equity - self.balance) / self.peak_equity
        daily_loss_pct = (
            abs(self.daily.realised_pnl) / self.daily.peak_equity if self.daily.peak_equity > 0 else 0.0
        )
        risk_val = abs(signal.entry_price - signal.stop_loss)
        reward_val = abs(signal.take_profit - signal.entry_price)
        rr_ratio = reward_val / risk_val if risk_val > 0 else 0.0

        decision_chain = {
            "circuit_breaker": {
                "passed": self._check_circuit_breaker(),
                "drawdown": float(drawdown),
                "limit": 0.15,
            },
            "daily_loss": {
                "passed": self._check_daily_loss(),
                "loss_pct": float(daily_loss_pct),
                "limit": float(self.cfg.max_daily_loss),
            },
            "max_positions": {
                "passed": self._check_max_positions(),
                "current": len(self.open_positions),
                "limit": self.cfg.max_positions,
            },
            "symbol_allocation": {
                "passed": self._check_symbol_allocation(signal.symbol),
                "symbol": signal.symbol,
            },
            "min_confidence": {
                "passed": self._check_minimum_confidence(signal.confidence),
                "confidence": float(signal.confidence),
                "threshold": 0.55,
            },
            "risk_reward": {
                "passed": self._check_risk_reward(signal),
                "ratio": float(rr_ratio),
                "threshold": 1.5,
            },
            "consecutive_losses": {
                "passed": self._check_consecutive_losses(),
                "current": self.daily.consecutive_losses,
                "limit": self.cfg.max_losing_streak,
            },
            "model_health": {
                "passed": self._check_model_health(model_health),
                "metrics": model_health,
            },
        }

        passed = all(d["passed"] for d in decision_chain.values())

        # Log to Audit Trail
        try:
            audit = get_audit_logger()
            audit.log_risk_decision(
                symbol=signal.symbol,
                direction=signal.direction,
                decision_chain=decision_chain,
                passed=passed,
            )

            # Log high-severity events specifically
            if not decision_chain["circuit_breaker"]["passed"]:
                audit.log_operator_action(
                    operator="system",
                    action="circuit_breaker_triggered",
                    reason=f"Hard drawdown limit hit during signal validation for {signal.symbol}",
                    metadata={"symbol": signal.symbol, "drawdown": float(drawdown)},
                )

            if not decision_chain["daily_loss"]["passed"]:
                audit.log_operator_action(
                    operator="system",
                    action="daily_loss_limit_triggered",
                    reason=f"Daily loss limit reached during signal validation for {signal.symbol}",
                    metadata={"symbol": signal.symbol, "loss_pct": float(daily_loss_pct)},
                )

        except (RuntimeError, ImportError):
            logger.debug("AuditLogger not available for risk decision logging")

        if not passed:
            rejection_reasons = [k for k, d in decision_chain.items() if not d["passed"]]
            reason_str = ", ".join(rejection_reasons)
            logger.warning(
                "Signal REJECTED | %s %s | Failed: %s",
                signal.symbol,
                signal.direction,
                reason_str,
            )
            if self.trade_logger:
                self.trade_logger.log_risk_event(
                    event_type="SIGNAL_REJECTED",
                    description=f"Failed filters: {reason_str}",
                    symbol=signal.symbol,
                    signal_id=signal_id,
                )
        return passed

    def reset_daily(self) -> None:
        """
        Reset daily stats and log a summary to the audit trail.
        Ensures daily performance is attributable and traceable.
        """
        summary = {
            "realised_pnl": float(self.daily.realised_pnl),
            "trade_count": int(self.daily.trade_count),
            "date": str(self.daily.date),
        }

        # Call parent to send monitor alerts and reset stats
        super().reset_daily()

        try:
            audit = get_audit_logger()
            audit.log(
                actor="system",
                action="daily_summary",
                details=f"Daily summary: PnL={summary['realised_pnl']:.2f}, Trades={summary['trade_count']}",
                metadata=summary,
            )
        except (RuntimeError, ImportError):
            logger.debug("AuditLogger not available for daily summary logging")
