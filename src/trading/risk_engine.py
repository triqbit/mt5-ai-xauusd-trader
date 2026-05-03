"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_engine.py
Institutional risk engine implementing cascading circuit breakers,
ATR-based position sizing, and drawdown protection.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Dict, Optional

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
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

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
    Enterprise risk authority.
    Enforces RISK_LIMITS.md safeguards.
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
        logger.info("RiskEngine initialised | balance=%.2f", account_balance)

    def calculate_atr_position_size(
        self,
        equity: float,
        atr: float,
        symbol: str,
        risk_per_trade: Optional[float] = None,
    ) -> float:
        """
        Calculate position size based on ATR and equity risk.
        Enforces max 10% equity nominal value per trade.
        """
        risk_pct = risk_per_trade or self.cfg.risk_per_trade
        # ATR-based sizing: stop distance is typically 2*ATR
        stop_dist = 2 * atr
        if stop_dist <= 0:
            return 0.01

        # Risk amount in currency
        risk_amount = equity * risk_pct

        # Simple lot calculation (assuming 1.0 pip value for simplicity in this scaffold)
        # In production, this should use symbol-specific tick value logic
        lots = risk_amount / (stop_dist * 100) # placeholder for actual pip/tick math

        # Enforce Max Position Size: 10% of account equity per trade nominal
        # Assuming gold (XAUUSD) ~2300 price, 1 lot = 100 oz
        # Nominal = lots * 100 * price
        price_estimate = 2300.0 # placeholder
        max_nominal = equity * self.cfg.max_equity_risk_per_trade
        max_lots_by_nominal = max_nominal / (100 * price_estimate)

        lots = min(lots, max_lots_by_nominal)
        lots = max(0.01, min(lots, 10.0)) # Hard cap for safety in scaffold
        lots = round(lots, 2)

        return lots

    def check_daily_loss_cascading(self) -> float:
        """
        Check cascading daily loss levels.
        Returns: sizing_multiplier (1.0, 0.5, 0.25, or 0.0 for HALT)
        """
        if self.daily.peak_equity <= 0:
            return 1.0

        loss_pct = abs(self.daily.realised_pnl) / self.daily.peak_equity
        if self.daily.realised_pnl >= 0:
            return 1.0

        if loss_pct >= self.cfg.daily_loss_limit_hard:
            logger.critical("HARD STOP: Daily loss %.2f%% hit 6%%", loss_pct * 100)
            return 0.0
        if loss_pct >= self.cfg.daily_loss_limit_l4:
            logger.error("LEVEL 4: Daily loss %.2f%% - HALT TRADING", loss_pct * 100)
            return 0.0
        if loss_pct >= self.cfg.daily_loss_limit_l3:
            logger.warning("LEVEL 3: Daily loss %.2f%% - Reduce size to 25%%", loss_pct * 100)
            return 0.25
        if loss_pct >= self.cfg.daily_loss_limit_l2:
            logger.warning("LEVEL 2: Daily loss %.2f%% - Reduce size to 50%%", loss_pct * 100)
            return 0.50
        if loss_pct >= self.cfg.daily_loss_limit_l1:
            logger.info("LEVEL 1: Daily loss %.2f%% - Yellow Alert", loss_pct * 100)
            return 1.0

        return 1.0

    def check_drawdown_levels(self) -> float:
        """
        Check peak-to-valley drawdown levels.
        Returns: sizing_multiplier
        """
        drawdown = (self.peak_equity - self.balance) / self.peak_equity

        if drawdown >= self.cfg.drawdown_limit_l5: # 30%
            logger.critical("DRAWDOWN L5: %.2f%% - FORCE CLOSE", drawdown * 100)
            return 0.0
        if drawdown >= self.cfg.drawdown_limit_l4: # 25%
            logger.error("DRAWDOWN L4: %.2f%% - HALT NEW", drawdown * 100)
            return 0.0
        if drawdown >= self.cfg.drawdown_limit_l3: # 20%
            return 0.50
        if drawdown >= self.cfg.drawdown_limit_l2: # 15%
            return 0.75

        return 1.0

    def validate_signal(self, signal: TradeSignal) -> bool:
        """
        Full institutional validation suite.
        """
        # 1. Circuit Breakers
        if self.check_daily_loss_cascading() == 0.0:
            return False
        if self.check_drawdown_levels() == 0.0:
            return False

        # 2. Streak Limits
        if self.daily.consecutive_losses >= self.cfg.max_losing_streak:
            logger.warning("Halt: Max losing streak reached (%d)", self.daily.consecutive_losses)
            return False

        # 3. Trade Count
        if self.daily.trade_count >= self.cfg.max_trades_per_day:
            logger.warning("Halt: Max daily trades reached (%d)", self.cfg.max_trades_per_day)
            return False

        return True

    def update_stats(self, pnl: float) -> None:
        """Update metrics after trade close."""
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

    def reset_daily(self) -> None:
        """Daily reset at 00:00 UTC."""
        self.daily = DailyStats(date=date.today(), peak_equity=self.balance)
        logger.info("RiskEngine daily stats reset.")

__all__ = ["RiskEngine", "TradeSignal", "DailyStats"]
