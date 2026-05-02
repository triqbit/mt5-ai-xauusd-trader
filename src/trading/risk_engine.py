"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_engine.py
Enterprise risk management engine implementing:
  - Cascading circuit breakers (Level 1-4 for loss, Level 1-5 for drawdown)
  - ATR-based position sizing
  - Maximum losing streak limits
  - Signal validation gate
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional

from src.core.config import TradingConfig
from src.core.monitor import Monitor
from src.core.trade_logger import TradeLogger
from src.trading.risk_manager import DailyStats, TradeSignal

logger = logging.getLogger(__name__)


@dataclass
class ExecutionDecision:
    """Detailed response from the RiskEngine about a signal."""

    signal: TradeSignal
    is_approved: bool
    confidence_score: float
    blocked_by: Optional[str] = None


class RiskEngine:
    """
    Institutional-grade risk authority.
    Implements granular circuit breakers and dynamic sizing as per RISK_LIMITS.md.
    """

    def __init__(
        self,
        config: TradingConfig,
        account_balance: float,
        logger_db: Optional[TradeLogger] = None,
        monitor: Optional[Monitor] = None,
    ) -> None:
        self.cfg = config
        self.balance = account_balance
        self.peak_equity = account_balance
        self.daily = DailyStats(peak_equity=account_balance)
        self.open_positions: Dict[str, int] = {}  # symbol -> ticket
        self.trade_logger = logger_db
        self.monitor = monitor
        self.losing_streak = 0
        logger.info("RiskEngine initialised | balance=%.2f", account_balance)

    def validate_signal(self, signal: TradeSignal) -> ExecutionDecision:
        """Full validation gate for a signal."""
        rejection_reason = None

        # 1. System-wide circuit breakers
        if not self._check_drawdown_breaker():
            rejection_reason = "Drawdown circuit breaker"
        elif not self._check_daily_loss_breaker():
            rejection_reason = "Daily loss circuit breaker"
        elif not self._check_losing_streak():
            rejection_reason = "Max losing streak reached"

        # 2. Portfolio & Strategy limits
        elif len(self.open_positions) >= self.cfg.max_positions:
            rejection_reason = "Max concurrent positions reached"
        elif signal.confidence < self.cfg.min_confidence:
            rejection_reason = f"Confidence {signal.confidence:.2f} < {self.cfg.min_confidence}"

        # 3. Trade-level sanity
        elif not self._check_risk_reward(signal):
            rejection_reason = "Insufficient Risk-Reward ratio"

        is_approved = rejection_reason is None

        if not is_approved:
            logger.warning("Signal REJECTED | %s | Reason: %s", signal.symbol, rejection_reason)

        return ExecutionDecision(
            signal=signal,
            is_approved=is_approved,
            confidence_score=signal.confidence,
            blocked_by=rejection_reason,
        )

    def calculate_lot_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        atr: float,
        account_equity: float,
        contract_size: float = 100.0,
        risk_multiplier: float = 2.0,
    ) -> float:
        """
        ATR-based position sizing with risk per trade limit.
        Uses ATR for volatility-adjusted scaling.
        """
        if atr <= 0 or entry_price <= 0:
            return 0.01

        # Calculate risk amount in dollars
        risk_per_trade_dollars = account_equity * self.cfg.risk_per_trade

        # Sizing based on ATR: Lot = Risk / (ATR * Multiplier * ContractSize)
        # This is a standard institutional approach to normalize risk by volatility.
        volatility_risk_per_unit = atr * risk_multiplier

        if volatility_risk_per_unit == 0:
            return 0.01

        raw_lot = risk_per_trade_dollars / (volatility_risk_per_unit * contract_size)

        # Adjust for stop loss distance if provided and greater than ATR-based risk
        price_risk = abs(entry_price - stop_loss)
        if price_risk > 0:
            sl_lot = risk_per_trade_dollars / (price_risk * contract_size)
            raw_lot = min(raw_lot, sl_lot)

        lot_size = round(raw_lot, 2)

        # Hard cap at 10% of equity (nominal value)
        nominal_value = lot_size * entry_price * contract_size
        if nominal_value > account_equity * 0.10:
            lot_size = (account_equity * 0.10) / (entry_price * contract_size)
            lot_size = round(lot_size, 2)

        return max(0.01, lot_size)

    def update_performance(self, pnl: float, current_equity: float) -> None:
        """Update metrics after trade closure."""
        self.balance = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        self.daily.realised_pnl += pnl
        self.daily.trade_count += 1

        if pnl < 0:
            self.losing_streak += 1
        else:
            self.losing_streak = 0

        if current_equity > self.daily.peak_equity:
            self.daily.peak_equity = current_equity

        if self.monitor:
            self.monitor.log_equity(current_equity)

    def reset_daily(self) -> None:
        """Daily maintenance."""
        if self.monitor:
            self.monitor.send_daily_summary(self.daily.realised_pnl, self.daily.trade_count)
        self.daily = DailyStats(peak_equity=self.balance)
        logger.info("RiskEngine: Daily stats reset.")

    # -- Internal Breakers --------------------------------------------------

    def _check_drawdown_breaker(self) -> bool:
        """Cascading Drawdown levels."""
        drawdown = (self.peak_equity - self.balance) / (self.peak_equity + 1e-9)

        levels = self.cfg.drawdown_levels
        if drawdown >= levels.get("5", 0.30):
            logger.critical("DRAWDOWN LEVEL 5: CRITICAL HALT")
            return False
        if drawdown >= levels.get("4", 0.25):
            logger.error("DRAWDOWN LEVEL 4: HALT NEW POSITIONS")
            return False
        return True

    def _check_daily_loss_breaker(self) -> bool:
        """Cascading Daily Loss levels."""
        if self.daily.peak_equity <= 0:
            return True

        loss_pct = abs(self.daily.realised_pnl) / self.daily.peak_equity
        if self.daily.realised_pnl >= 0:
            return True

        levels = self.cfg.daily_loss_levels
        if loss_pct >= levels.get("hard", 0.06):
            logger.critical("DAILY LOSS HARD STOP: CRITICAL HALT")
            return False
        if loss_pct >= levels.get("4", 0.05):
            logger.error("DAILY LOSS LEVEL 4: EMERGENCY HALT")
            return False
        return True

    def _check_losing_streak(self) -> bool:
        if self.losing_streak >= self.cfg.max_losing_streak:
            logger.warning("Max losing streak (%d) reached.", self.cfg.max_losing_streak)
            return False
        return True

    def _check_risk_reward(self, signal: TradeSignal, min_rr: float = 1.5) -> bool:
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.entry_price)
        if risk == 0:
            return False
        return (reward / risk) >= min_rr


__all__ = ["ExecutionDecision", "RiskEngine"]
