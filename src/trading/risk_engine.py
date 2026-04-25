"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_engine.py
Enterprise risk management engine implementing:
  - Institutional cascading loss limits (2% - 6%)
  - ATR-based dynamic position sizing
  - 5-level drawdown circuit breakers (10% - 30%)
  - Multi-layer signal validation
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, Optional

from src.core.config import TradingConfig
from src.core.monitor import Monitor
from src.core.trade_logger import TradeLogger

logger = logging.getLogger(__name__)

# Ray Dalio All-Weather allocation weights
ALLOCATION_WEIGHTS: Dict[str, float] = {
    "XAUUSD": 0.18,  # Gold - inflation hedge
    "USDCHF": 0.15,  # CHF - deflation hedge
    "GBPUSD": 0.13,  # GBP - growth / balanced
    "EURUSD": 0.12,  # EUR - growth / balanced
    "XAGUSD": 0.12,  # Silver - commodity
    "AUDUSD": 0.15,  # AUD - commodity currency
    "USDJPY": 0.08,  # JPY - carry trade
    "EURJPY": 0.07,  # EUR/JPY cross
}


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
    trade_count: int = 0
    peak_equity: float = 0.0


class RiskEngine:
    """
    Central risk authority.
    Enforces institutional risk limits and circuit breakers.
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
        self.open_positions: Dict[str, int] = {}  # symbol -> ticket
        self.trade_logger = logger_db
        self.monitor = monitor
        logger.info("RiskEngine initialised | balance=%.2f", account_balance)

    def approve(self, signal: TradeSignal, signal_id: Optional[int] = None) -> bool:
        """
        Run the full validation cascade.
        Returns True only if ALL layers pass.
        """
        rejection_reason = ""
        if not self.check_circuit_breaker():
            rejection_reason = "Circuit breaker active"
        elif not self._check_daily_loss():
            rejection_reason = "Daily loss limit reached"
        elif not self._check_max_positions():
            rejection_reason = "Max positions reached"
        elif not self._check_minimum_confidence(signal.confidence):
            rejection_reason = f"Confidence {signal.confidence:.2f} too low"
        elif not self._check_risk_reward(signal):
            rejection_reason = "Risk-Reward ratio too low"

        passed = rejection_reason == ""
        if not passed:
            logger.warning(
                "Signal REJECTED | %s %s | Reason: %s",
                signal.symbol,
                signal.direction,
                rejection_reason,
            )
            if self.trade_logger:
                self.trade_logger.log_risk_event(
                    event_type="SIGNAL_REJECTED",
                    description=rejection_reason,
                    symbol=signal.symbol,
                    signal_id=signal_id,
                )
        return passed

    def size_position(
        self,
        symbol: str,
        atr: float,
        risk_fraction: Optional[float] = None,
        contract_multiplier: float = 100.0,
    ) -> float:
        """
        ATR-based position sizing with institutional scaling.

        Args:
            symbol: Trading symbol.
            atr: Average True Range.
            risk_fraction: Override for risk percentage per trade.
            contract_multiplier: Multiplier to convert price change to currency units (e.g., 100 for Gold).
        """
        if atr <= 0:
            return 0.01

        # Use configured risk per trade if not overridden
        risk_pct = risk_fraction or self.cfg.risk_per_trade

        # Apply cascading loss scaling
        loss_pct = 0.0
        if self.daily.peak_equity > 0:
             loss_pct = abs(min(0, self.daily.realised_pnl)) / self.daily.peak_equity

        if loss_pct >= self.cfg.daily_loss_limit_lv3:
            risk_pct *= 0.25
        elif loss_pct >= self.cfg.daily_loss_limit_lv2:
            risk_pct *= 0.50

        # Apply drawdown scaling
        drawdown = (self.peak_equity - self.balance) / self.peak_equity
        if drawdown >= self.cfg.drawdown_limit_lv3:
            risk_pct *= 0.50
        elif drawdown >= self.cfg.drawdown_limit_lv2:
            risk_pct *= 0.75

        risk_amount = self.balance * risk_pct
        # Lot calculation: risk / (atr * 2 * contract_multiplier)
        lot_size = risk_amount / (atr * 2 * contract_multiplier)
        lot_size = max(0.01, min(round(lot_size, 2), 10.0))

        return lot_size

    def check_circuit_breaker(self) -> bool:
        """Drawdown-based circuit breaker."""
        drawdown = (self.peak_equity - self.balance) / self.peak_equity

        if drawdown >= self.cfg.drawdown_limit_lv5:
            logger.critical("CIRCUIT BREAKER: 30%% Drawdown reached. HALTING.")
            return False
        if drawdown >= self.cfg.drawdown_limit_lv4:
            logger.warning("CIRCUIT BREAKER: 25%% Drawdown reached. Halt new positions.")
            return False

        return True

    def _check_daily_loss(self) -> bool:
        if self.daily.peak_equity <= 0:
            return True
        loss_pct = abs(min(0, self.daily.realised_pnl)) / self.daily.peak_equity

        if loss_pct >= self.cfg.daily_loss_limit_lv4:
            logger.critical("DAILY LOSS HALT: 5%% reached.")
            return False
        return True

    def _check_max_positions(self) -> bool:
        if len(self.open_positions) >= self.cfg.max_concurrent_positions:
            return False
        return True

    def _check_minimum_confidence(self, confidence: float) -> bool:
        return confidence >= self.cfg.min_confidence

    def _check_risk_reward(self, signal: TradeSignal, min_rr: float = 1.5) -> bool:
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.entry_price)
        if risk == 0:
            return False
        return (reward / risk) >= min_rr

    def update_equity(self, current_equity: float) -> None:
        self.balance = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        if current_equity > self.daily.peak_equity:
            self.daily.peak_equity = current_equity

    def record_pnl(self, pnl: float) -> None:
        self.daily.realised_pnl += pnl
        self.daily.trade_count += 1

    def reset_daily(self) -> None:
        if self.monitor:
            self.monitor.send_daily_summary(
                self.daily.realised_pnl, self.daily.trade_count
            )
        self.daily = DailyStats(peak_equity=self.balance)
        logger.info("Daily stats reset")


__all__ = ["DailyStats", "RiskEngine", "TradeSignal"]
