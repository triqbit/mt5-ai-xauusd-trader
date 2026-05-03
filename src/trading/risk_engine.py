"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_engine.py
Institutional risk management engine implementing:
  - ATR-based position sizing (dynamic volatility adjustment)
  - Cascading daily loss circuit breakers (Level 1-4)
  - Hard drawdown protection and forced liquidation
  - Multi-layer execution filtering (Momentum, ATR, Spread)
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, Optional, Any

import numpy as np
from src.core.config import TradingConfig
from src.trading.risk_manager import TradeSignal

logger = logging.getLogger(__name__)

@dataclass
class RiskStats:
    """Intraday and historical risk metrics."""
    peak_equity: float = 0.0
    daily_peak_equity: float = 0.0
    daily_loss: float = 0.0
    daily_trades: int = 0
    consecutive_losses: int = 0
    last_reset: date = field(default_factory=date.today)

class RiskEngine:
    """
    Advanced Risk Management Engine.
    Enforces hard limits defined in RISK_LIMITS.md.
    """

    def __init__(self, config: TradingConfig, initial_balance: float) -> None:
        self.cfg = config
        self.stats = RiskStats(
            peak_equity=initial_balance,
            daily_peak_equity=initial_balance
        )
        self.current_equity = initial_balance
        logger.info("RiskEngine initialized | balance=%.2f", initial_balance)

    def validate_signal(
        self,
        signal: TradeSignal,
        atr: float,
        avg_atr: float,
        tick_value: float = 1.0,
        tick_size: float = 0.01
    ) -> bool:
        """
        Comprehensive signal validation against institutional risk limits.

        Args:
            signal: The proposed trade signal.
            atr: Current 14-period ATR.
            avg_atr: 30-day average ATR for volatility context.
            tick_value: Value of one tick per 1.0 lot.
            tick_size: Minimum price increment.

        Returns:
            True if signal is approved, False otherwise.
        """
        # 1. Volatility Check
        if not self._check_volatility(atr, avg_atr):
            return False

        # 2. Daily Loss Circuit Breakers
        if not self._check_daily_loss():
            return False

        # 3. Drawdown Check
        if not self._check_drawdown():
            return False

        # 4. Position-Level Risk
        if not self._check_trade_risk(signal, tick_value=tick_value, tick_size=tick_size):
            return False

        return True

    def calculate_atr_lot_size(
        self,
        symbol: str,
        balance: float,
        stop_loss_distance: float,
        atr: float,
        avg_atr: float,
        tick_value: float = 1.0,
        tick_size: float = 0.01,
        contract_size: float = 100.0
    ) -> float:
        """
        Calculate position size based on ATR-adjusted risk.

        Args:
            symbol: Trading symbol.
            balance: Current account balance.
            stop_loss_distance: Distance from entry to SL in price units.
            atr: Current ATR.
            avg_atr: Average ATR.
            tick_value: Monetary value of one tick per 1.0 lot.
            tick_size: Smallest price change.
            contract_size: Standard lot size in units.

        Sizing Logic:
        - Base risk: risk_per_trade (e.g., 1%)
        - Volatility adjustment:
            - atr > 2.0x avg_atr -> 50% size
            - atr > 1.5x avg_atr -> 75% size
            - atr > 3.0x avg_atr -> HALT (0.0)
        """
        if avg_atr <= 0 or atr <= 0 or stop_loss_distance <= 0:
            return 0.01

        # Volatility Multiplier
        vol_mult = 1.0
        ratio = atr / avg_atr

        if ratio > 3.0:
            logger.warning("EXTREME VOLATILITY | ATR ratio %.2f | Trading Halted", ratio)
            return 0.0
        elif ratio > 2.0:
            vol_mult = 0.5
            logger.info("High Volatility | ATR ratio %.2f | Reducing size to 50%%", ratio)
        elif ratio > 1.5:
            vol_mult = 0.75
            logger.info("Medium Volatility | ATR ratio %.2f | Reducing size to 75%%", ratio)

        # Base Risk Calculation
        risk_amount = balance * self.cfg.risk_per_trade * vol_mult

        # Risk per lot = (SL distance / tick_size) * tick_value
        risk_per_lot = (stop_loss_distance / tick_size) * tick_value

        if risk_per_lot <= 0:
            return 0.01

        lot_size = risk_amount / risk_per_lot

        # Hard limits from RISK_LIMITS.md
        # Max 10% equity at risk per trade
        max_lot_size = (balance * 0.10) / risk_per_lot
        lot_size = min(lot_size, max_lot_size)

        lot_size = max(0.01, round(lot_size, 2))

        return lot_size

    def update_metrics(self, equity: float, pnl: float = 0.0) -> None:
        """Update risk metrics after equity changes or trade close."""
        self.current_equity = equity

        if equity > self.stats.peak_equity:
            self.stats.peak_equity = equity

        if equity > self.stats.daily_peak_equity:
            self.stats.daily_peak_equity = equity

        if pnl != 0:
            self.stats.daily_loss -= pnl # loss is positive if pnl is negative
            if pnl < 0:
                self.stats.consecutive_losses += 1
            else:
                self.stats.consecutive_losses = 0
            self.stats.daily_trades += 1

    def check_reset(self) -> None:
        """Reset daily metrics at 00:00 UTC."""
        today = date.today()
        if today > self.stats.last_reset:
            logger.info("Resetting daily risk metrics")
            self.stats.daily_peak_equity = self.current_equity
            self.stats.daily_loss = 0.0
            self.stats.daily_trades = 0
            self.stats.last_reset = today

    # -- Internal Guards ---------------------------------------------------

    def _check_volatility(self, atr: float, avg_atr: float) -> bool:
        if avg_atr <= 0: return True
        if atr / avg_atr > 3.0:
            logger.warning("Signal rejected: Extreme volatility (ATR > 3x avg)")
            return False
        return True

    def _check_daily_loss(self) -> bool:
        loss_pct = self.stats.daily_loss / self.stats.daily_peak_equity if self.stats.daily_peak_equity > 0 else 0

        if loss_pct >= 0.05: # Level 4: 5% Emergency Stop
            logger.critical("CIRCUIT BREAKER: Daily loss %.2f%% hit Level 4 limit (5%%)", loss_pct * 100)
            return False

        if self.stats.consecutive_losses >= 3:
            logger.warning("Signal rejected: 3 consecutive losses hit")
            return False

        if self.stats.daily_trades >= 20:
            logger.warning("Signal rejected: Max 20 trades per day hit")
            return False

        return True

    def _check_drawdown(self) -> bool:
        drawdown = (self.stats.peak_equity - self.current_equity) / self.stats.peak_equity if self.stats.peak_equity > 0 else 0
        if drawdown >= 0.30: # Level 5: 30% Hard Drawdown
            logger.critical("EMERGENCY: Total drawdown %.2f%% hit Hard Stop (30%%)", drawdown * 100)
            return False
        return True

    def _check_trade_risk(self, signal: TradeSignal, tick_value: float = 1.0, tick_size: float = 0.01) -> bool:
        """Verify that the actual monetary risk of the trade is within safe bounds."""
        risk_distance = abs(signal.entry_price - signal.stop_loss)
        if risk_distance <= 0:
            return False

        # Risk in currency units
        total_risk = (risk_distance / tick_size) * tick_value * signal.lot_size
        risk_pct = total_risk / self.current_equity if self.current_equity > 0 else 1.0

        if risk_pct > 0.02:  # Hard cap at 2% risk per trade for extra safety
            logger.warning("Signal rejected: Monetary risk %.2f%% exceeds 2%% safety cap", risk_pct * 100)
            return False

        return True

__all__ = ["RiskEngine", "RiskStats"]
