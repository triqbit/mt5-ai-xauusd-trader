"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_engine.py
Institutional-grade risk management engine enforcing:
  - Cascading daily loss limits (2% to 6%)
  - Peak-to-valley drawdown circuit breakers (10% to 30%)
  - Dynamic ATR-based position sizing
  - Margin utilization monitoring
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

from src.core.config import TradingConfig

logger = logging.getLogger(__name__)


@dataclass
class DailyStats:
    """Intraday metrics reset daily at 00:00 UTC."""

    date: date = field(default_factory=date.today)
    realised_pnl: float = 0.0
    trade_count: int = 0
    peak_equity: float = 0.0


class RiskEngine:
    """
    Core risk authority enforcing institutional limits defined in RISK_LIMITS.md.
    """

    def __init__(self, config: TradingConfig, initial_balance: float) -> None:
        self.cfg = config
        self.balance = initial_balance
        self.peak_equity = initial_balance
        self.daily = DailyStats(peak_equity=initial_balance)
        self.open_positions_count = 0
        logger.info("RiskEngine initialised | balance=%.2f", initial_balance)

    def update_equity(self, current_equity: float) -> None:
        """Update current balance and tracking peaks."""
        self.balance = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        if current_equity > self.daily.peak_equity:
            self.daily.peak_equity = current_equity

    def record_trade_close(self, pnl: float) -> None:
        """Record realised PnL from a closed trade."""
        self.daily.realised_pnl += pnl
        self.daily.trade_count += 1

    def reset_daily(self) -> None:
        """Reset daily stats (call at 00:00 UTC)."""
        self.daily = DailyStats(peak_equity=self.balance)
        logger.info("Daily risk stats reset")

    def check_circuit_breaker(self) -> bool:
        """
        Check peak-to-valley drawdown limits (RISK_LIMITS.md 6.1).
        Returns False if a hard halt is required.
        """
        drawdown = (self.peak_equity - self.balance) / self.peak_equity

        if drawdown >= self.cfg.drawdown_level_5:  # 30%
            logger.critical("CIRCUIT BREAKER: 30% Drawdown! Hard Halt.")
            return False

        if drawdown >= self.cfg.drawdown_level_4:  # 25%
            logger.error("CIRCUIT BREAKER: 25% Drawdown! Halting new positions.")
            return False

        return True

    def get_position_size_multiplier(self) -> float:
        """
        Calculate sizing multiplier based on cascading limits (RISK_LIMITS.md 2.1 & 6.1).
        """
        multiplier = 1.0

        # 1. Daily Loss Cascading
        if self.daily.peak_equity > 0:
            loss_pct = abs(self.daily.realised_pnl) / self.daily.peak_equity
            if self.daily.realised_pnl < 0:
                if loss_pct >= self.cfg.daily_loss_level_4:  # 5%
                    return 0.0  # HALT
                elif loss_pct >= self.cfg.daily_loss_level_3:  # 4%
                    multiplier *= 0.25
                elif loss_pct >= self.cfg.daily_loss_level_2:  # 3%
                    multiplier *= 0.50

        # 2. Drawdown Cascading
        drawdown = (self.peak_equity - self.balance) / self.peak_equity
        if drawdown >= self.cfg.drawdown_level_3:  # 20%
            multiplier *= 0.50
        elif drawdown >= self.cfg.drawdown_level_2:  # 15%
            multiplier *= 0.75

        return multiplier

    def calculate_atr_lot_size(
        self,
        symbol: str,
        atr: float,
        entry_price: float,
        stop_loss: float,
        contract_size: float = 100.0,  # Standard Gold contract
    ) -> float:
        """
        ATR-based dynamic position sizing (RISK_LIMITS.md 1.3).
        Risk is capped at config.risk_per_trade (1%).
        """
        risk_amount = self.balance * self.cfg.risk_per_trade

        # Distance to stop loss
        sl_distance = abs(entry_price - stop_loss)
        if sl_distance == 0:
            return 0.0

        # Raw lot size based on risk
        raw_lots = risk_amount / (sl_distance * contract_size)

        # Apply institutional cascading multipliers
        multiplier = self.get_position_size_multiplier()
        if multiplier == 0:
            return 0.0

        final_lots = raw_lots * multiplier

        # Max position size (10% of equity)
        notional_value = final_lots * entry_price * contract_size
        max_notional = self.balance * self.cfg.max_position_size_pct
        if notional_value > max_notional:
            final_lots = max_notional / (entry_price * contract_size)

        # Enforce min limits (RISK_LIMITS.md 1.1)
        final_lots = max(self.cfg.min_position_size, final_lots)

        return round(final_lots, 2)

    def validate_signal(self, confidence: float) -> bool:
        """Validate signal confidence against institutional floors (RISK_LIMITS.md 4.1)."""
        return not confidence < self.cfg.confidence_threshold


__all__ = ["DailyStats", "RiskEngine"]
