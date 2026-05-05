"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_engine.py
Enterprise risk management engine implementing:
  - ATR-based position sizing (14-period vs 30-day average)
  - Cascading daily loss circuit breakers (Level 1-4)
  - Drawdown safeguards and exposure limits
  - Signal validation against hard risk limits
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

import pandas as pd

from src.core.config import TradingConfig
from src.core.monitor import Monitor
from src.core.trade_logger import TradeLogger

logger = logging.getLogger(__name__)


@dataclass
class RiskDecision:
    """Decision details from the RiskEngine."""

    is_approved: bool
    reason: str = ""
    adjusted_lot_size: float = 0.0


@dataclass
class DailyStats:
    """Intraday PnL tracker reset each trading day."""

    date: date = field(default_factory=date.today)
    realised_pnl: float = 0.0
    trade_count: int = 0
    peak_equity: float = 0.0
    consecutive_losses: int = 0


class RiskEngine:
    """
    Institutional risk engine.
    Enforces RISK_LIMITS.md safeguards.
    """

    def __init__(
        self,
        config: TradingConfig,
        account_balance: float,
        trade_logger: Optional[TradeLogger] = None,
        monitor: Optional[Monitor] = None,
    ) -> None:
        self.cfg = config
        self.balance = account_balance
        self.peak_equity = account_balance
        self.daily = DailyStats(peak_equity=account_balance)
        self.trade_logger = trade_logger
        self.monitor = monitor
        logger.info("RiskEngine initialised | balance=%.2f", account_balance)

    def validate_signal(
        self, signal: Any, market_data: pd.DataFrame, open_positions: list[dict[str, Any]]
    ) -> RiskDecision:
        """
        Validate a trade signal against all risk layers.
        """
        # 1. Circuit Breakers
        if not self._check_drawdown_breaker():
            return RiskDecision(False, "Hard drawdown limit reached")

        if not self._check_daily_loss_breaker():
            return RiskDecision(False, "Daily loss limit reached (Level 4)")

        if self.daily.trade_count >= self.cfg.max_trades_per_day:
            return RiskDecision(False, "Max daily trades reached")

        if self.daily.consecutive_losses >= self.cfg.max_losing_streak:
            return RiskDecision(False, "Max consecutive losses reached")

        # 2. Exposure Limits
        if len(open_positions) >= self.cfg.max_positions:
            return RiskDecision(False, "Max concurrent positions reached")

        # 3. Sizing & Confidence
        if signal.confidence < self.cfg.min_confidence:
            return RiskDecision(
                False, f"Confidence {signal.confidence:.2f} below {self.cfg.min_confidence}"
            )

        # ATR-based position sizing adjustment
        adjusted_lots = self.calculate_position_size(signal.symbol, market_data)

        if adjusted_lots < self.cfg.min_lot_size:
            return RiskDecision(False, f"Calculated lot size {adjusted_lots} below minimum")

        return RiskDecision(True, "Approved", adjusted_lots)

    def calculate_position_size(self, symbol: str, market_data: pd.DataFrame) -> float:
        """
        ATR-based position sizing.
        Compares 14-period ATR to 30-day (approx 8640 M5 bars) average.
        """
        if market_data.empty or "atr" not in market_data.columns:
            logger.warning("No ATR data available for sizing, using default risk.")
            return self.cfg.min_lot_size

        current_atr = market_data["atr"].iloc[-1]
        avg_atr = market_data["atr"].tail(8640).mean()  # Approx 30 days of M5 data

        multiplier = 1.0
        ratio = current_atr / avg_atr if avg_atr > 0 else 1.0

        if ratio > self.cfg.volatility_extreme_threshold:
            logger.warning("Extreme volatility (%.2fx) - HALTING", ratio)
            return 0.0
        if ratio > self.cfg.volatility_very_high_threshold:
            multiplier = 0.5
        elif ratio > self.cfg.volatility_high_threshold:
            multiplier = 0.75

        # Basic risk-based sizing: risk 1% of balance
        # For XAUUSD, 1 lot = 100 oz. $1 move = $100 per lot.
        # Simplified: lot_size = (balance * risk_per_trade) / (ATR * 100)
        risk_amount = self.balance * self.cfg.risk_per_trade
        lot_size = (risk_amount / (current_atr * 100)) * multiplier

        # Cap at Max Position Size (10% of equity)
        max_notional = self.balance * self.cfg.max_position_size_pct
        price = market_data["close"].iloc[-1]
        max_lots = max_notional / (price * 100)

        final_lots = min(lot_size, max_lots)
        final_lots = max(self.cfg.min_lot_size, round(final_lots, 2))

        return final_lots

    def update_metrics(self, current_equity: float, realized_pnl: float = 0) -> None:
        """Update internal trackers."""
        self.balance = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        if realized_pnl != 0:
            self.daily.realised_pnl += realized_pnl
            self.daily.trade_count += 1
            if realized_pnl < 0:
                self.daily.consecutive_losses += 1
            else:
                self.daily.consecutive_losses = 0

        if current_equity > self.daily.peak_equity:
            self.daily.peak_equity = current_equity

    # -- Internal Breakers --------------------------------------------------
    def _check_drawdown_breaker(self) -> bool:
        drawdown = (self.peak_equity - self.balance) / self.peak_equity
        return drawdown < self.cfg.max_drawdown

    def _check_daily_loss_breaker(self) -> bool:
        if self.daily.peak_equity <= 0:
            return True
        loss_pct = abs(self.daily.realised_pnl) / self.daily.peak_equity
        return not (self.daily.realised_pnl < 0 and loss_pct >= self.cfg.max_daily_loss)

    def get_daily_loss_level(self) -> int:
        """Returns cascading loss level 0-4."""
        if self.daily.peak_equity <= 0:
            return 0
        loss_pct = abs(self.daily.realised_pnl) / self.daily.peak_equity
        if self.daily.realised_pnl >= 0:
            return 0

        if loss_pct >= self.cfg.max_daily_loss:
            return 4
        if loss_pct >= self.cfg.daily_loss_lvl3:
            return 3
        if loss_pct >= self.cfg.daily_loss_lvl2:
            return 2
        if loss_pct >= self.cfg.daily_loss_lvl1:
            return 1
        return 0


__all__ = ["RiskEngine", "RiskDecision", "DailyStats"]
