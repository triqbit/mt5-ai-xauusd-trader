"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_engine.py
Institutional-grade risk engine implementing cascading limits,
ATR-based position sizing, and drawdown circuit breakers.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

from src.core.config import TradingConfig
from src.trading.risk_manager import TradeSignal

logger = logging.getLogger(__name__)

@dataclass
class DailyRiskStats:
    """Intraday risk tracker for cascading limits."""
    date: date = field(default_factory=date.today)
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    equity_peak: float = 0.0
    trade_count: int = 0

class RiskEngine:
    """
    Enterprise risk management engine.
    Enforces RISK_LIMITS.md through multiple cascading validation layers.
    """

    def __init__(self, config: TradingConfig) -> None:
        """
        Initialize the RiskEngine.

        Args:
            config: TradingConfig object containing risk parameters.
        """
        self.cfg = config
        self.stats = DailyRiskStats()
        self.total_peak_equity: float = 0.0

    def update_metrics(self, balance: float, equity: float, realized_pnl: float) -> None:
        """
        Update real-time account metrics for risk calculations.

        Args:
            balance: Current account balance.
            equity: Current account equity.
            realized_pnl: Realized P&L for the current day.
        """
        if self.stats.date != date.today():
            self.stats = DailyRiskStats(equity_peak=equity)

        self.stats.realized_pnl = realized_pnl
        self.stats.unrealized_pnl = equity - balance

        if equity > self.stats.equity_peak:
            self.stats.equity_peak = equity

        if equity > self.total_peak_equity:
            self.total_peak_equity = equity

    def check_signal(self, signal: TradeSignal, current_drawdown: float, atr: float, atr_sma: float) -> bool:
        """
        Proactively validate a signal against circuit breakers.

        Args:
            signal: The TradeSignal to validate.
            current_drawdown: Current peak-to-valley drawdown percentage (0.0 to 1.0).
            atr: Current Average True Range.
            atr_sma: 30-period SMA of ATR for volatility scaling.

        Returns:
            True if signal is allowed, False otherwise.
        """
        # 1. Equity Drawdown Circuit Breaker (RISK_LIMITS.md Section 6.1)
        if current_drawdown >= self.cfg.drawdown_halt_pct:
            logger.error("SIGNAL REJECTED: Drawdown circuit breaker (%.1f%% >= %.1f%%)",
                         current_drawdown * 100, self.cfg.drawdown_halt_pct * 100)
            return False

        # 2. Daily Loss Circuit Breaker (RISK_LIMITS.md Section 2.1)
        daily_loss_pct = abs(min(0, self.stats.realized_pnl)) / (self.stats.equity_peak or 1.0)
        if daily_loss_pct >= self.cfg.daily_loss_halt_pct:
            logger.error("SIGNAL REJECTED: Daily loss circuit breaker (%.1f%% >= %.1f%%)",
                         daily_loss_pct * 100, self.cfg.daily_loss_halt_pct * 100)
            return False

        # 3. Volatility Check (RISK_LIMITS.md Section 5.1)
        vol_ratio = atr / (atr_sma or 1.0)
        if vol_ratio >= self.cfg.volatility_extreme_threshold:
            logger.error("SIGNAL REJECTED: Extreme volatility (ATR ratio %.2f >= %.2f)",
                         vol_ratio, self.cfg.volatility_extreme_threshold)
            return False

        # 4. Confidence Floor (RISK_LIMITS.md Section 4.1)
        if signal.confidence < self.cfg.confidence_threshold:
            logger.warning("SIGNAL REJECTED: Confidence too low (%.2f < %.2f)",
                           signal.confidence, self.cfg.confidence_threshold)
            return False

        return True

    def calculate_position_size(
        self,
        balance: float,
        stop_loss_dist: float,
        current_drawdown: float,
        atr: float,
        atr_sma: float,
        tick_value: float = 1.0,
        tick_size: float = 0.01
    ) -> float:
        """
        Calculate dynamic position size based on risk parameters and market conditions.
        Enterprise-ready formula: Lot Size = Risk Amount / (SL Distance * Tick Value / Tick Size)

        Args:
            balance: Current account balance.
            stop_loss_dist: Stop loss distance in price units.
            current_drawdown: Current drawdown percentage.
            atr: Current ATR.
            atr_sma: 30-period SMA of ATR.
            tick_value: Monetary value of a single tick for 1.0 lot.
            tick_size: Minimum price change (tick size).

        Returns:
            Calculated lot size.
        """
        if stop_loss_dist <= 0 or tick_value <= 0 or tick_size <= 0:
            return 0.0

        # Base risk capital
        base_risk = balance * self.cfg.risk_per_trade

        # 1. Daily Loss Cascading (RISK_LIMITS.md Section 2.1)
        daily_loss_pct = abs(min(0, self.stats.realized_pnl)) / (self.stats.equity_peak or 1.0)
        loss_multiplier = 1.0
        if daily_loss_pct >= self.cfg.daily_loss_quarter_size_pct:
            loss_multiplier = 0.25
        elif daily_loss_pct >= self.cfg.daily_loss_half_size_pct:
            loss_multiplier = 0.5

        # 2. Drawdown Cascading (RISK_LIMITS.md Section 6.1)
        drawdown_multiplier = 1.0
        if current_drawdown >= self.cfg.drawdown_50pct_size_pct:
            drawdown_multiplier = 0.50
        elif current_drawdown >= self.cfg.drawdown_75pct_size_pct:
            drawdown_multiplier = 0.75

        # 3. Volatility Scaling (RISK_LIMITS.md Section 5.1)
        vol_ratio = atr / (atr_sma or 1.0)
        vol_multiplier = 1.0
        if vol_ratio >= self.cfg.volatility_very_high_threshold:
            vol_multiplier = 0.50
        elif vol_ratio >= self.cfg.volatility_high_threshold:
            vol_multiplier = 0.75

        # Final risk capital
        final_risk = base_risk * loss_multiplier * drawdown_multiplier * vol_multiplier

        # Institutional Lot Sizing formula
        # risk_per_tick = tick_value
        # risk_per_unit = tick_value / tick_size
        # lot_size = final_risk / (stop_loss_dist * risk_per_unit)

        lot_size = final_risk / (stop_loss_dist * (tick_value / tick_size))

        # Enforce hard constraints (RISK_LIMITS.md Section 1.1)
        lot_size = max(0.01, min(lot_size, 10.0))
        lot_size = round(lot_size, 2)

        return lot_size

__all__ = ["RiskEngine", "DailyRiskStats"]
