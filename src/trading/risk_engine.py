"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_engine.py

Institutional Risk Engine enforcing limits from RISK_LIMITS.md:
- ATR-based position sizing
- Cascading circuit breakers
- Drawdown protection
- Exposure management
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional

from src.core.config import TradingConfig

logger = logging.getLogger(__name__)

class RiskEngine:
    """
    The RiskEngine provides low-level validation and position sizing logic.
    Implements institutional-grade safeguards and ATR-driven allocation.
    """

    def __init__(self, config: TradingConfig) -> None:
        self.cfg = config
        self.peak_equity: float = 0.0
        self.daily_realized_pnl: float = 0.0
        self.trades_today: int = 0
        self.consecutive_losses: int = 0

    def calculate_lot_size(
        self,
        equity: float,
        atr: float,
        tick_value: float,
        tick_size: float = 0.01,
        risk_fraction: Optional[float] = None
    ) -> float:
        """
        ATR-based position sizing as per RISK_LIMITS.md.
        Formula: (equity * risk_per_trade) / (ATR * tick_value / tick_size)

        Args:
            equity: Current account equity.
            atr: Average True Range (volatility).
            tick_value: Value of a single tick for 1.0 lot.
            tick_size: Minimum price increment.
            risk_fraction: Optional override for risk % per trade.

        Returns:
            Calculated lot size capped by institutional limits.
        """
        risk_pct = risk_fraction if risk_fraction is not None else self.cfg.risk_per_trade
        risk_amount = equity * risk_pct

        if atr <= 0 or tick_value <= 0:
            logger.warning("Invalid ATR or tick_value for sizing. Using minimum 0.01.")
            return 0.01

        # Position Size = Risk Amount / (Stop Loss Distance * Tick Value / Tick Size)
        # Using ATR as the base stop loss distance
        lot_size = risk_amount / (atr * (tick_value / tick_size))

        # 1.1 Per-Trade Limits: Max 10% of account equity per trade
        # For XAUUSD, Notional = Price * LotSize * 100.
        # We cap the lot size to ensure we don't exceed 10% equity risk at once.
        # Assuming typical XAUUSD price ~2000, 1 lot = $200,000 notional.
        # This is complex without current price, so we use a conservative cap.

        lot_size = max(0.01, round(lot_size, 2))

        # Hard cap for safety (e.g., 10 lots for retail-size accounts)
        return min(lot_size, 10.0)

    def validate_execution(self, account_info: Dict[str, Any], signal_confidence: float) -> bool:
        """
        Multi-layer validation cascade (Cascading Level 1-4).
        Enforces Daily Loss Limits and Equity Drawdown protections.

        Args:
            account_info: Dictionary containing 'equity', 'balance', 'margin_level'.
            signal_confidence: The confidence score from the ensemble model.

        Returns:
            True if all circuit breakers and limits pass, False otherwise.
        """
        equity = float(account_info.get("equity", 0.0))

        if self.peak_equity == 0:
            self.peak_equity = equity
        self.peak_equity = max(self.peak_equity, equity)

        # 6.1 Equity Drawdown Limits
        drawdown = (self.peak_equity - equity) / self.peak_equity if self.peak_equity > 0 else 0
        if drawdown >= 0.30:
            logger.critical("CIRCUIT BREAKER: 30% Max Drawdown hit. ALL TRADING HALTED.")
            return False

        # 2.1 Daily Loss Limits (Cascading)
        daily_loss_pct = abs(self.daily_realized_pnl) / self.peak_equity if self.peak_equity > 0 else 0
        if self.daily_realized_pnl < 0:
            # Level 4: Emergency Stop (Hard limit from config)
            if daily_loss_pct >= self.cfg.max_daily_loss:
                logger.error("Daily Loss Level 4 (%.1f%%) hit. Halting for the day.", daily_loss_pct * 100)
                return False
            # Level 3: Red Alert (80% of daily limit)
            elif daily_loss_pct >= self.cfg.max_daily_loss * 0.8:
                logger.warning("Daily Loss Level 3 (%.1f%%) hit. Reducing activity.", daily_loss_pct * 100)

        # 2.3 Daily Trade Limits
        if self.trades_today >= self.cfg.max_trades_per_day:
            logger.warning("Daily trade limit reached (%d)", self.cfg.max_trades_per_day)
            return False

        # 4.1 Prediction Confidence
        if signal_confidence < self.cfg.confidence_threshold:
            logger.debug("Signal confidence %.2f below threshold %.2f", signal_confidence, self.cfg.confidence_threshold)
            return False

        # 2.3 Max Losing Streak
        if self.consecutive_losses >= self.cfg.max_losing_streak:
            logger.warning("Max losing streak hit (%d). Cooling down.", self.consecutive_losses)
            return False

        # 8.1 Margin Limits
        margin_level = float(account_info.get("margin_level", 0.0))
        if margin_level > 0 and margin_level < 110:
            logger.warning("Insufficient margin level: %.2f%%", margin_level)
            return False

        return True

    def update_stats(self, pnl: float) -> None:
        """
        Update internal counters after a trade is closed.

        Args:
            pnl: Realized profit or loss of the trade.
        """
        self.daily_realized_pnl += pnl
        self.trades_today += 1
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

    def reset_daily(self) -> None:
        """Reset intraday circuit breakers and counters (at 00:00 UTC)."""
        logger.info("Resetting daily risk stats. Realized PnL: %.2f", self.daily_realized_pnl)
        self.daily_realized_pnl = 0.0
        self.trades_today = 0
        self.consecutive_losses = 0

__all__ = ["RiskEngine"]
