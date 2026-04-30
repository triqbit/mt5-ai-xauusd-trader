"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_engine.py
Institutional-grade risk management engine implementing:
  - Cascading Circuit Breakers (Levels 1-4)
  - ATR-based Position Sizing
  - Multi-level Drawdown Protection
  - Losing Streak Limits
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, Optional, List

import numpy as np
from src.core.config import TradingConfig
from src.core.monitor import Monitor
from src.core.trade_logger import TradeLogger

logger = logging.getLogger(__name__)

@dataclass
class TradeSignal:
    """Validated trading signal passed to order execution."""
    symbol: str
    direction: int  # +1 buy / -1 sell
    entry_price: float
    stop_loss: float
    take_profit: float
    lot_size: float
    algorithm: str
    confidence: float  # 0.0 - 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class DailyStats:
    """Intraday PnL tracker reset each trading day."""
    date: date = field(default_factory=date.today)
    realised_pnl: float = 0.0
    unrealised_pnl: float = 0.0
    trade_count: int = 0
    consecutive_losses: int = 0
    peak_equity: float = 0.0

class RiskEngine:
    """
    Institutional risk engine.
    Enforces RISK_LIMITS.md through cascading circuit breakers and ATR-based sizing.
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
        self.open_positions: Dict[str, List[int]] = {}  # symbol -> [tickets]
        self.trade_logger = logger_db
        self.monitor = monitor

        # Risk level tracking
        self.current_risk_multiplier = 1.0
        self.trading_halted = False

        logger.info("RiskEngine initialized | balance=%.2f", account_balance)

    def approve_signal(self, signal: TradeSignal) -> bool:
        """
        Final validation before execution.
        """
        if self.trading_halted:
            logger.warning("Trading is HALTED due to risk limit breach.")
            return False

        rejection_reason = ""

        # 1. Check Circuit Breakers
        if not self._check_circuit_breakers():
            rejection_reason = "Circuit Breaker Active"

        # 2. Check Daily Limits
        elif not self._check_daily_limits():
            rejection_reason = "Daily Limits Exceeded"

        # 3. Check Losing Streak
        elif self.daily.consecutive_losses >= self.cfg.max_losing_streak:
            rejection_reason = f"Max Losing Streak ({self.cfg.max_losing_streak}) Reached"

        # 4. Check Max Positions
        elif self._count_total_positions() >= self.cfg.max_positions:
            rejection_reason = "Max Positions Reached"

        # 5. Check Minimum Confidence
        elif signal.confidence < self.cfg.confidence_threshold:
            rejection_reason = f"Confidence {signal.confidence:.2f} < {self.cfg.confidence_threshold}"

        if rejection_reason:
            logger.warning("Signal REJECTED | %s | Reason: %s", signal.symbol, rejection_reason)
            if self.trade_logger:
                self.trade_logger.log_risk_event(
                    event_type="SIGNAL_REJECTED",
                    description=rejection_reason,
                    symbol=signal.symbol
                )
            return False

        return True

    def calculate_lot_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        atr: float,
        pip_value: Optional[float] = None
    ) -> float:
        """
        Calculate position size based on ATR and Risk Per Trade.
        """
        # Default pip_value for XAUUSD if not provided
        if pip_value is None:
            pip_value = 100.0 if "XAUUSD" in symbol else 10.0

        risk_amount = self.balance * self.cfg.risk_per_trade * self.current_risk_multiplier

        # ATR-based volatility sizing (Risk 1% at 2*ATR distance)
        # Or simple SL-based sizing if SL is provided
        risk_per_unit = abs(entry_price - stop_loss) if stop_loss else (2 * atr)

        if risk_per_unit <= 0:
            return 0.01

        lot_size = risk_amount / (risk_per_unit * pip_value)

        # Enforce hard limits
        lot_size = max(0.01, round(lot_size, 2))

        # Max 10% equity per trade limit
        max_notional = self.balance * 0.10
        notional_value = lot_size * entry_price
        if notional_value > max_notional:
            lot_size = max(0.01, round(max_notional / entry_price, 2))

        return lot_size

    def update_performance(self, current_equity: float, realised_pnl: Optional[float] = None) -> None:
        """
        Update internal state with latest account data.
        """
        self.balance = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        if realised_pnl is not None:
            self.daily.realised_pnl += realised_pnl
            self.daily.trade_count += 1
            if realised_pnl < 0:
                self.daily.consecutive_losses += 1
            else:
                self.daily.consecutive_losses = 0

        if self.balance > self.daily.peak_equity:
            self.daily.peak_equity = self.balance

        # Re-evaluate circuit breakers
        self._check_circuit_breakers()
        self._check_daily_limits()

    def reset_daily(self) -> None:
        """Reset daily stats at market open."""
        self.daily = DailyStats(peak_equity=self.balance)
        self.current_risk_multiplier = 1.0
        self.trading_halted = False
        logger.info("Daily risk stats reset.")

    # -- Internal Risk Logic --

    def _check_circuit_breakers(self) -> bool:
        """Cascading drawdown protection."""
        drawdown = (self.peak_equity - self.balance) / self.peak_equity

        # Level 5: Emergency Halt (30%)
        if drawdown >= self.cfg.drawdown_levels[5]:
            self.trading_halted = True
            logger.critical("CIRCUIT BREAKER LEVEL 5: Drawdown %.1f%%. TRADING HALTED.", drawdown * 100)
            return False

        # Levels 2-4: Position Reduction
        if drawdown >= self.cfg.drawdown_levels[4]:
            self.current_risk_multiplier = 0.0 # Stop new positions
        elif drawdown >= self.cfg.drawdown_levels[3]:
            self.current_risk_multiplier = 0.50
        elif drawdown >= self.cfg.drawdown_levels[2]:
            self.current_risk_multiplier = 0.75
        else:
            self.current_risk_multiplier = 1.0

        return True

    def _check_daily_limits(self) -> bool:
        """Cascading daily loss protection."""
        if self.daily.peak_equity <= 0:
            return True

        daily_loss_pct = abs(self.daily.realised_pnl) / self.daily.peak_equity
        if self.daily.realised_pnl >= 0:
            return True

        # Level 4: Emergency Stop (5%)
        if daily_loss_pct >= self.cfg.daily_loss_levels[4]:
            self.trading_halted = True
            logger.critical("DAILY STOP LEVEL 4: Loss %.1f%%. TRADING HALTED.", daily_loss_pct * 100)
            return False

        # Level 2-3: Reduce Sizing
        if daily_loss_pct >= self.cfg.daily_loss_levels[3]:
            self.current_risk_multiplier = min(self.current_risk_multiplier, 0.25)
        elif daily_loss_pct >= self.cfg.daily_loss_levels[2]:
            self.current_risk_multiplier = min(self.current_risk_multiplier, 0.50)

        return True

    def _count_total_positions(self) -> int:
        return sum(len(p) for p in self.open_positions.values())

__all__ = ["RiskEngine", "TradeSignal", "DailyStats"]
