"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_engine.py
Enterprise risk management engine implementing:
  - ATR-based dynamic position sizing
  - Cascading daily loss circuit breakers
  - Multi-level drawdown protection
  - Margin & exposure limits
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Any

from src.core.config import TradingConfig

logger = logging.getLogger(__name__)

@dataclass
class DailyRiskStats:
    """Intraday risk metrics reset each trading day."""
    date: date = field(default_factory=lambda: datetime.now(timezone.utc).date())
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    equity_peak: float = 0.0
    trade_count: int = 0
    consecutive_losses: int = 0
    consecutive_wins: int = 0

class RiskEngine:
    """
    Institutional-grade risk engine enforcing RISK_LIMITS.md.
    """

    def __init__(self, config: TradingConfig) -> None:
        """
        Initialize the Risk Engine.

        Args:
            config: TradingConfig object.
        """
        self.cfg = config
        self.stats = DailyRiskStats()
        self.account_equity_peak: float = 0.0
        self._is_halted: bool = False

    def check_signal(self, symbol: str, direction: int, confidence: float, current_equity: float, open_positions_count: int) -> Dict[str, Any]:
        """
        Perform a full risk check for a new signal.

        Args:
            symbol: Trading symbol.
            direction: +1 for Buy, -1 for Sell.
            confidence: Model confidence (0.0 - 1.0).
            current_equity: Current account equity.
            open_positions_count: Number of currently open positions.

        Returns:
            Dictionary with 'approved' (bool) and 'reason' (str).
        """
        # 1. System Halt Check
        if self._is_halted:
            return {"approved": False, "reason": "Trading system is HALTED due to critical risk breach."}

        # 2. Daily Loss Cascading Checks
        daily_loss_pct = abs(self.stats.realized_pnl) / self.stats.equity_peak if self.stats.equity_peak > 0 else 0
        if self.stats.realized_pnl < 0:
            if daily_loss_pct >= self.cfg.daily_loss_limit_hard:
                self._is_halted = True
                return {"approved": False, "reason": f"Daily HARD STOP reached ({daily_loss_pct:.2%})"}
            if daily_loss_pct >= self.cfg.daily_loss_limit_lvl4:
                return {"approved": False, "reason": f"Daily Emergency Stop reached ({daily_loss_pct:.2%})"}

        # 3. Drawdown Cascading Checks
        if current_equity > self.account_equity_peak:
            self.account_equity_peak = current_equity

        drawdown_pct = (self.account_equity_peak - current_equity) / self.account_equity_peak if self.account_equity_peak > 0 else 0
        if drawdown_pct >= self.cfg.drawdown_limit_hard:
            self._is_halted = True
            return {"approved": False, "reason": f"Account HARD DRAWDOWN limit reached ({drawdown_pct:.2%})"}
        if drawdown_pct >= self.cfg.drawdown_limit_lvl4:
            return {"approved": False, "reason": f"Account drawdown Halt New Positions reached ({drawdown_pct:.2%})"}

        # 4. Position Count Limit
        if open_positions_count >= self.cfg.max_positions:
            return {"approved": False, "reason": f"Max concurrent positions reached ({self.cfg.max_positions})"}

        # 5. Confidence Threshold
        if confidence < self.cfg.confidence_threshold:
            return {"approved": False, "reason": f"Confidence {confidence:.2f} below threshold {self.cfg.confidence_threshold:.2f}"}

        return {"approved": True, "reason": "All risk checks passed."}

    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        atr: float,
        current_equity: float,
        confidence: float
    ) -> float:
        """
        Calculate ATR-based position size with confidence scaling.

        Args:
            symbol: Trading symbol.
            entry_price: Planned entry price.
            stop_loss: Planned stop loss price.
            atr: Average True Range (14-period).
            current_equity: Current account equity.
            confidence: Model confidence (0.0 - 1.0).

        Returns:
            Lot size (minimum 0.01).
        """
        # Risk capital per trade
        risk_per_trade_pct = self.cfg.risk_per_trade

        # Adjust risk based on confidence (as per RISK_LIMITS.md section 4.1)
        confidence_multiplier = 1.0
        if confidence < 0.55:
            return 0.0  # Skip trade
        elif confidence < 0.65:
            confidence_multiplier = 0.5
        # 0.65+ is 100% sizing

        # Daily loss scaling
        daily_loss_pct = abs(self.stats.realized_pnl) / self.stats.equity_peak if self.stats.equity_peak > 0 else 0
        loss_multiplier = 1.0
        if self.stats.realized_pnl < 0:
            if daily_loss_pct >= self.cfg.daily_loss_limit_lvl3:
                loss_multiplier = 0.25
            elif daily_loss_pct >= self.cfg.daily_loss_limit_lvl2:
                loss_multiplier = 0.50

        # Drawdown scaling
        drawdown_pct = (self.account_equity_peak - current_equity) / self.account_equity_peak if self.account_equity_peak > 0 else 0
        dd_multiplier = 1.0
        if drawdown_pct >= self.cfg.drawdown_limit_lvl3:
            dd_multiplier = 0.50
        elif drawdown_pct >= self.cfg.drawdown_limit_lvl2:
            dd_multiplier = 0.75

        effective_risk_pct = risk_per_trade_pct * confidence_multiplier * loss_multiplier * dd_multiplier
        risk_amount = current_equity * effective_risk_pct

        # Distance to stop loss
        sl_distance = abs(entry_price - stop_loss)
        if sl_distance == 0:
            return 0.01

        # Standardize lot size for Gold (usually 100 oz per lot, but depends on broker)
        # Assuming 1 pip = 0.01 for Gold, and we want to risk 'risk_amount'
        # Lot Size = Risk Amount / (SL Distance * Pip Value per Lot)
        # For XAUUSD, 1.0 lot usually means $100 per $1 move.
        # If sl_distance is $5.00, then 1 lot risks $500.
        # lot_size = risk_amount / (sl_distance * 100)

        lot_size = risk_amount / (sl_distance * 100)

        # Max Position Size: 10% of equity per trade
        max_lot_size = (current_equity * 0.10) / (sl_distance * 100) if sl_distance > 0 else 0.1
        lot_size = min(lot_size, max_lot_size)

        # Floor and Round
        lot_size = max(0.01, round(lot_size, 2))

        return lot_size

    def update_stats(self, pnl: float, is_win: bool) -> None:
        """Update daily stats after a trade closes."""
        self.stats.realized_pnl += pnl
        self.stats.trade_count += 1

        if is_win:
            self.stats.consecutive_wins += 1
            self.stats.consecutive_losses = 0
        else:
            self.stats.consecutive_losses += 1
            self.stats.consecutive_wins = 0

    def reset_daily(self, current_equity: float) -> None:
        """Reset daily stats at 00:00 UTC."""
        self.stats = DailyRiskStats(equity_peak=current_equity)
        self._is_halted = False
        logger.info("Risk Engine: Daily stats reset. Equity peak: %.2f", current_equity)

    def update_peak_equity(self, current_equity: float) -> None:
        """Update account-level equity peak for drawdown calculation."""
        if current_equity > self.account_equity_peak:
            self.account_equity_peak = current_equity
        if current_equity > self.stats.equity_peak:
            self.stats.equity_peak = current_equity

__all__ = ["RiskEngine", "DailyRiskStats"]
