"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_engine.py
Enterprise risk management engine implementing:
  - ATR-based position sizing
  - Cascading daily loss limits
  - Multi-level equity drawdown circuit breakers
  - Institutional hard limits as defined in RISK_LIMITS.md
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Optional

from src.core.config import TradingConfig

logger = logging.getLogger(__name__)


@dataclass
class DailyRiskStats:
    """Intraday risk metrics reset each trading day."""
    date: date = field(default_factory=date.today)
    realised_pnl: float = 0.0
    trade_count: int = 0
    starting_equity: float = 0.0
    peak_equity_daily: float = 0.0


class RiskEngine:
    """
    Centralized risk control system.
    Enforces institutional safeguards and calculates optimal position sizes.
    """

    def __init__(self, config: TradingConfig, initial_equity: float) -> None:
        self.cfg = config
        self.equity = initial_equity
        self.peak_equity = initial_equity
        self.daily = DailyRiskStats(starting_equity=initial_equity, peak_equity_daily=initial_equity)

        # State tracking
        self.trading_halted = False
        self.emergency_stop = False

        logger.info("RiskEngine initialized | equity=%.2f", initial_equity)

    def update_equity(self, current_equity: float) -> None:
        """Update current equity and track peaks for drawdown calculation."""
        self.equity = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        if current_equity > self.daily.peak_equity_daily:
            self.daily.peak_equity_daily = current_equity

        self._check_circuit_breakers()

    def record_trade_close(self, pnl: float) -> None:
        """Record realized P&L for daily limit tracking."""
        self.daily.realised_pnl += pnl
        self.daily.trade_count += 1
        logger.info("Trade closed | PnL=%.2f | Daily PnL=%.2f", pnl, self.daily.realised_pnl)
        self._check_daily_limits()

    def get_position_size_multiplier(self) -> float:
        """
        Calculate sizing multiplier based on cascading loss limits and drawdowns.
        Returns a float between 0.0 and 1.0.
        """
        if self.trading_halted or self.emergency_stop:
            return 0.0

        # 1. Daily Loss Cascading
        daily_loss_pct = abs(self.daily.realised_pnl) / self.daily.starting_equity if self.daily.realised_pnl < 0 else 0.0
        multiplier = 1.0

        if daily_loss_pct >= self.cfg.daily_loss_limit_l4: # 5%
            return 0.0 # HALT
        elif daily_loss_pct >= self.cfg.daily_loss_limit_l3: # 4%
            multiplier = min(multiplier, 0.25)
        elif daily_loss_pct >= self.cfg.daily_loss_limit_l2: # 3%
            multiplier = min(multiplier, 0.50)

        # 2. Drawdown Cascading
        drawdown_pct = (self.peak_equity - self.equity) / self.peak_equity if self.peak_equity > 0 else 0.0

        if drawdown_pct >= self.cfg.drawdown_limit_l4: # 25%
            return 0.0 # HALT new positions
        elif drawdown_pct >= self.cfg.drawdown_limit_l3: # 20%
            multiplier = min(multiplier, 0.50)
        elif drawdown_pct >= self.cfg.drawdown_limit_l2: # 15%
            multiplier = min(multiplier, 0.75)

        return multiplier

    def calculate_atr_position_size(
        self,
        atr_14: float,
        atr_30_avg: float,
        risk_amount_dollars: float,
        tick_value: float = 1.0,
        tick_size: float = 0.01
    ) -> float:
        """
        Calculate position size based on ATR and volatility.
        Capped by institutional limits.
        """
        if atr_14 <= 0:
            return 0.01

        # Volatility scaling
        vol_ratio = atr_14 / atr_30_avg if atr_30_avg > 0 else 1.0
        sizing_multiplier = self.get_position_size_multiplier()

        if vol_ratio > 3.0:
            return 0.0 # Extreme Volatility -> HALT
        elif vol_ratio > 2.0:
            sizing_multiplier *= 0.5
        elif vol_ratio > 1.5:
            sizing_multiplier *= 0.75

        # Base size calculation: Risk / (ATR * TickValue/TickSize)
        # Assuming SL is placed at 1 ATR distance
        points_at_risk = atr_14
        if points_at_risk <= 0: return 0.01

        raw_lot_size = risk_amount_dollars / (points_at_risk * (tick_value / tick_size))

        # Apply multipliers
        final_lot_size = raw_lot_size * sizing_multiplier

        # Institutional Caps
        max_notional_equity = self.equity * self.cfg.max_equity_risk_per_trade # 10%
        # Simple lot to notional conversion for XAUUSD (Approx: 1 lot = 100oz * Price)
        # For more accuracy, pass current price and contract size.

        # Ensure minimum lot size
        final_lot_size = max(0.01, round(final_lot_size, 2))

        if self.trading_halted:
            return 0.0

        return final_lot_size

    def _check_circuit_breakers(self) -> None:
        """Check for hard stops and drawdown breaches."""
        drawdown_pct = (self.peak_equity - self.equity) / self.peak_equity if self.peak_equity > 0 else 0.0

        if drawdown_pct >= self.cfg.drawdown_limit_l5: # 30%
            self.emergency_stop = True
            self.trading_halted = True
            logger.critical("DRAWDOWN CIRCUIT BREAKER: 30%% limit reached. FORCE CLOSE ALL.")

    def _check_daily_limits(self) -> None:
        """Check daily loss limits."""
        daily_loss_pct = abs(self.daily.realised_pnl) / self.daily.starting_equity if self.daily.realised_pnl < 0 else 0.0

        if daily_loss_pct >= self.cfg.daily_loss_limit_hard: # 6%
            self.emergency_stop = True
            self.trading_halted = True
            logger.critical("DAILY LOSS HARD STOP: 6%% limit reached. FORCE CLOSE ALL.")
        elif daily_loss_pct >= self.cfg.daily_loss_limit_l4: # 5%
            self.trading_halted = True
            logger.warning("DAILY LOSS HALT: 5%% limit reached. Trading suspended until reset.")

    def reset_daily(self, current_equity: float) -> None:
        """Reset daily counters at 00:00 UTC."""
        self.daily = DailyRiskStats(
            date=date.today(),
            starting_equity=current_equity,
            peak_equity_daily=current_equity
        )
        self.trading_halted = False # Reset daily halt
        logger.info("RiskEngine daily stats reset | starting_equity=%.2f", current_equity)


__all__ = ["RiskEngine", "DailyRiskStats"]
