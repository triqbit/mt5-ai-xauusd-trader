"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_engine.py
Enterprise risk management engine implementing:
  - ATR-based position sizing
  - Circuit breakers (Daily loss, Peak drawdown)
  - 6-layer entry filter cascade
  - Risk limits as defined in RISK_LIMITS.md
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional

from src.core.config import TradingConfig
from src.trading.risk_manager import TradeSignal, DailyStats, ALLOCATION_WEIGHTS

logger = logging.getLogger(__name__)


class RiskEngine:
    """
    Enhanced Risk Engine replacing RiskManager.
    Enforces strict risk limits and circuit breakers.
    """

    def __init__(self, config: TradingConfig, account_balance: float) -> None:
        self.cfg = config
        self.balance = account_balance
        self.peak_equity = account_balance
        self.daily = DailyStats(peak_equity=account_balance)
        self.open_positions: Dict[str, int] = {}  # symbol -> ticket
        logger.info("RiskEngine initialised | balance=%.2f", account_balance)

    def approve(self, signal: TradeSignal) -> bool:
        """
        Run the full 6-layer risk filter cascade.
        Returns True only if ALL layers pass.
        """
        # Layer 1: System-wide Circuit Breakers
        if not self._check_circuit_breakers():
            return False

        # Layer 2: Daily Limits
        if not self._check_daily_limits():
            return False

        # Layer 3: Exposure & Position Limits
        if not self._check_exposure_limits(signal):
            return False

        # Layer 4: Model Confidence
        if not self._check_confidence_limit(signal.confidence):
            return False

        # Layer 5: Risk/Reward Ratio
        if not self._check_risk_reward(signal):
            return False

        # Layer 6: Volatility/Market Conditions (Simplified)
        if not self._check_market_conditions(signal):
            return False

        logger.info("Signal APPROVED | %s %d | size=%.2f", signal.symbol, signal.direction, signal.lot_size)
        return True

    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        atr: float,
    ) -> float:
        """
        ATR-based position sizing with account risk limits.
        """
        if entry_price == stop_loss:
            return self.cfg.min_lot_size

        # Risk amount based on config (e.g., 1% of balance)
        risk_amount = self.balance * self.cfg.risk_per_trade

        # Risk per unit (in price)
        risk_per_unit = abs(entry_price - stop_loss)

        if risk_per_unit == 0:
            return self.cfg.min_lot_size

        # Raw lot size
        # Assuming Gold (XAUUSD) where 1 lot = 100 units.
        # Need to adjust based on symbol contract size if generic.
        contract_size = 100 if "XAU" in symbol else 100000

        raw_lot_size = risk_amount / (risk_per_unit * contract_size)

        # Apply Position-Level Limits from RISK_LIMITS.md
        # Max 10% of equity per trade
        max_lot_by_equity = (self.balance * self.cfg.max_position_size_percent) / (entry_price * contract_size / self.cfg.max_leverage)

        lot_size = min(raw_lot_size, max_lot_by_equity)
        lot_size = max(self.cfg.min_lot_size, round(lot_size, 2))

        logger.debug("Position Sizing | risk_amt=%.2f risk_unit=%.2f lots=%.2f", risk_amount, risk_per_unit, lot_size)
        return lot_size

    def update_equity(self, current_equity: float) -> None:
        """Update equity and peak tracking."""
        self.balance = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        if current_equity > self.daily.peak_equity:
            self.daily.peak_equity = current_equity

    def record_trade_closed(self, pnl: float) -> None:
        """Record realised PnL."""
        self.daily.realised_pnl += pnl
        self.daily.trade_count += 1

    # -- Internal Checks ----------------------------------------------------

    def _check_circuit_breakers(self) -> bool:
        """Check for catastrophic drawdown."""
        drawdown = (self.peak_equity - self.balance) / self.peak_equity
        if drawdown >= self.cfg.max_drawdown_limit:
            logger.critical("CIRCUIT BREAKER: Max drawdown reached (%.1f%%)", drawdown * 100)
            return False
        return True

    def _check_daily_limits(self) -> bool:
        """Check daily loss limits."""
        if self.daily.peak_equity <= 0:
            return True

        daily_loss_pct = abs(self.daily.realised_pnl) / self.daily.peak_equity
        if self.daily.realised_pnl < 0:
            if daily_loss_pct >= self.cfg.daily_loss_hard_stop:
                logger.critical("DAILY HARD STOP: Loss reached %.1f%%", daily_loss_pct * 100)
                return False
            if daily_loss_pct >= self.cfg.daily_loss_limit:
                logger.warning("DAILY LIMIT: Loss reached %.1f%% - Halting trading", daily_loss_pct * 100)
                return False

        if self.daily.trade_count >= 20: # Max trades per day
            logger.warning("DAILY LIMIT: Max trades reached (20)")
            return False

        return True

    def _check_exposure_limits(self, signal: TradeSignal) -> bool:
        """Check position count and exposure."""
        if len(self.open_positions) >= self.cfg.max_positions:
            logger.warning("LIMIT: Max concurrent positions reached (%d)", self.cfg.max_positions)
            return False

        if signal.symbol not in ALLOCATION_WEIGHTS:
            logger.warning("LIMIT: Symbol %s not in approved portfolio", signal.symbol)
            return False

        return True

    def _check_confidence_limit(self, confidence: float) -> bool:
        """Check model confidence."""
        if confidence < self.cfg.min_confidence:
            logger.debug("LIMIT: Confidence %.2f below threshold %.2f", confidence, self.cfg.min_confidence)
            return False
        return True

    def _check_risk_reward(self, signal: TradeSignal, min_rr: float = 1.5) -> bool:
        """Check risk/reward ratio."""
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.entry_price)
        if risk <= 0:
            return False
        rr = reward / risk
        if rr < min_rr:
            logger.debug("LIMIT: R:R %.2f below minimum %.2f", rr, min_rr)
            return False
        return True

    def _check_market_conditions(self, signal: TradeSignal) -> bool:
        """Placeholder for spread and news checks."""
        # In a real system, we'd check spread from MT5 here
        return True


__all__ = ["RiskEngine"]
