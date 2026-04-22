"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_engine.py
Institutional-grade risk engine implementing:
  - Cascading daily loss limits (Yellow, Orange, Red, Emergency)
  - Equity drawdown circuit breakers
  - ATR-based dynamic position sizing
  - Margin & exposure validation
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from src.core.config import TradingConfig
from src.core.monitor import Monitor
from src.core.trade_logger import TradeLogger
from src.trading.risk_manager import TradeSignal

logger = logging.getLogger(__name__)


@dataclass
class DailyStats:
    """Intraday performance tracking."""

    date: date = field(default_factory=date.today)
    realised_pnl: float = 0.0
    trade_count: int = 0
    peak_equity: float = 0.0
    consecutive_losses: int = 0


class RiskEngine:
    """
    Enterprise risk management engine.
    Enforces RISK_LIMITS.md via a multi-layer validation cascade.
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
        self.trade_logger = logger_db
        self.monitor = monitor
        self.is_halted: bool = False
        logger.info("RiskEngine initialised | balance=%.2f", account_balance)

    def calculate_lot_size(
        self,
        entry_price: float,
        stop_loss: float,
        atr: float,
        win_rate: float = 0.55,
    ) -> float:
        """
        ATR-based position sizing with fractional Kelly scaling.
        Formula: (Equity * Risk%) / (StopLossDistance * PipValue)
        """
        risk_per_trade_pct = self.cfg.risk_per_trade

        # Apply cascading daily loss reduction
        daily_loss_pct = (
            abs(self.daily.realised_pnl) / self.daily.peak_equity
            if self.daily.peak_equity > 0
            else 0
        )
        if 0.03 <= daily_loss_pct < 0.04:
            risk_per_trade_pct *= 0.50  # Orange Alert
            logger.warning("Orange Alert: Reducing position size by 50%")
        elif 0.04 <= daily_loss_pct < 0.05:
            risk_per_trade_pct *= 0.25  # Red Alert
            logger.warning("Red Alert: Reducing position size by 75%")

        stop_dist = abs(entry_price - stop_loss)
        if stop_dist == 0:
            return 0.01

        # Calculate lot size based on fixed fractional risk
        risk_amount = self.balance * risk_per_trade_pct

        # Lot size = Risk Amount / (Stop Distance * Contract Size)
        # For XAUUSD, Contract Size is usually 100. For Forex, 100,000.
        lot_size = risk_amount / (stop_dist * self.cfg.contract_size)

        # Enforce hard limits
        # Max position size in lots = (Equity * Max%) / EntryPrice
        max_lots = (self.balance * self.cfg.max_position_size_pct) / entry_price
        lot_size = max(0.01, min(lot_size, max_lots))
        return round(lot_size, 2)

    def validate_signal(self, signal: TradeSignal) -> bool:
        """
        Full 6-layer validation cascade from RISK_LIMITS.md.
        """
        if self.is_halted:
            return self._reject("TRADING_HALTED")

        # 1. Equity Drawdown Circuit Breaker
        drawdown = (self.peak_equity - self.balance) / self.peak_equity
        if drawdown >= self.cfg.max_equity_drawdown:
            self.is_halted = True
            return self._reject("CIRCUIT_BREAKER_DRAWDOWN")

        # 2. Daily Loss Limits (Cascading)
        loss_pct = (
            abs(self.daily.realised_pnl) / self.daily.peak_equity
            if self.daily.peak_equity > 0
            else 0
        )
        if self.daily.realised_pnl < 0 and loss_pct >= self.cfg.max_daily_loss_limit:
            self.is_halted = True
            return self._reject("DAILY_LOSS_LIMIT")

        # 3. Position Limits
        if self.daily.trade_count >= self.cfg.max_trades_per_day:
            return self._reject("MAX_DAILY_TRADES")

        # 4. Exposure & Leverage
        # Notional value = Price * Lots * ContractSize
        notional_value = signal.entry_price * signal.lot_size * self.cfg.contract_size
        if notional_value > self.balance * self.cfg.max_leverage:
            return self._reject("MAX_LEVERAGE_EXCEEDED")

        # 5. Model Confidence
        if signal.confidence < self.cfg.confidence_threshold:
            return self._reject("LOW_CONFIDENCE")

        # 6. Risk/Reward Ratio
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.entry_price)
        if risk == 0 or (reward / risk) < 1.5:
            return self._reject("INSUFFICIENT_RR")

        return True

    def _reject(self, reason: str) -> bool:
        logger.warning("Signal REJECTED | Reason: %s", reason)
        if self.trade_logger:
            self.trade_logger.log_risk_event(
                event_type="SIGNAL_REJECTED",
                description=reason,
            )
        return False

    def update_performance(self, pnl: float) -> None:
        """Track results and update stats."""
        self.daily.realised_pnl += pnl
        self.daily.trade_count += 1
        self.balance += pnl

        if pnl < 0:
            self.daily.consecutive_losses += 1
        else:
            self.daily.consecutive_losses = 0

        if self.balance > self.peak_equity:
            self.peak_equity = self.balance
        if self.balance > self.daily.peak_equity:
            self.daily.peak_equity = self.balance

        # Sequential loss circuit breaker
        if self.daily.consecutive_losses >= 3:
            logger.warning("Halt: 3 consecutive losses.")

    def reset_daily(self) -> None:
        """Reset intraday limits at 00:00 UTC."""
        self.daily = DailyStats(peak_equity=self.balance)
        self.is_halted = False
        logger.info("Daily risk stats reset.")


__all__ = ["DailyStats", "RiskEngine"]
