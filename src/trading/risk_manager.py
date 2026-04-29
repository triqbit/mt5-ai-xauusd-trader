"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_manager.py
Enterprise risk management engine implementing:
  - Kelly Criterion position sizing (fractional)
  - Ray Dalio All-Weather portfolio allocation
  - Dynamic drawdown protection & circuit breakers
  - 6-layer entry filter cascade
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from src.core.config import TradingConfig
from src.core.constants import ALLOCATION_WEIGHTS
from src.core.monitor import Monitor
from src.core.trade_logger import TradeLogger

logger = logging.getLogger(__name__)


class TradeSignal(BaseModel):
    """
    Validated trading signal passed to order execution.
    Enforces strict typing and value constraints using Pydantic.
    """

    symbol: str = Field(..., description="Trading symbol (e.g., 'XAUUSD').")
    direction: Literal[1, -1] = Field(..., description="Trade direction: 1 for BUY, -1 for SELL.")
    entry_price: float = Field(..., gt=0, description="Target entry price.")
    stop_loss: float = Field(..., gt=0, description="Stop loss price.")
    take_profit: float = Field(..., gt=0, description="Take profit price.")
    lot_size: float = Field(..., gt=0, description="Position size in lots.")
    algorithm: str = Field(..., description="Algorithm that generated the signal.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence (0.0 to 1.0).")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("stop_loss", "take_profit")
    @classmethod
    def validate_prices(cls, v: float, info) -> float:
        """Ensure SL and TP are on the correct side of entry price."""
        if "entry_price" not in info.data or "direction" not in info.data:
            return v

        entry = info.data["entry_price"]
        direction = info.data["direction"]

        if info.field_name == "stop_loss":
            if direction == 1 and v >= entry:
                raise ValueError("Stop loss must be below entry price for BUY signals.")
            if direction == -1 and v <= entry:
                raise ValueError("Stop loss must be above entry price for SELL signals.")
        elif info.field_name == "take_profit":
            if direction == 1 and v <= entry:
                raise ValueError("Take profit must be above entry price for BUY signals.")
            if direction == -1 and v >= entry:
                raise ValueError("Take profit must be below entry price for SELL signals.")
        return v


@dataclass
class DailyStats:
    """Intraday PnL tracker reset each trading day."""

    date: date = field(default_factory=date.today)
    realised_pnl: float = 0.0
    trade_count: int = 0
    peak_equity: float = 0.0


class RiskManager:
    """
    Central risk authority.
    Every signal must be approved here before reaching the order router.
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
        logger.info("RiskManager initialised | balance=%.2f", account_balance)

    # -- Public API ---------------------------------------------------------
    def approve(self, signal: TradeSignal, signal_id: Optional[int] = None) -> bool:
        """
        Run the full 6-layer risk filter cascade.
        Returns True only if ALL layers pass.
        """
        rejection_reason = ""
        if not self._check_circuit_breaker():
            rejection_reason = "Circuit breaker active"
        elif not self._check_daily_loss():
            rejection_reason = "Daily loss limit reached"
        elif not self._check_max_positions():
            rejection_reason = "Max positions reached"
        elif not self._check_symbol_allocation(signal.symbol):
            rejection_reason = f"Symbol {signal.symbol} not in portfolio"
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
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        pip_value: float = 1.0,
    ) -> float:
        """
        Fractional Kelly Criterion position sizing.
        Returns lot size capped at max risk per trade.
        """
        if avg_loss == 0:
            return 0.01  # minimum lot
        kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        kelly_fraction = max(0.0, min(kelly_fraction, 0.25))  # cap at 25% Kelly
        risk_capital = self.balance * self.cfg.risk_per_trade
        lot_size = (risk_capital * kelly_fraction) / (avg_loss * pip_value)
        lot_size = max(0.01, round(lot_size, 2))
        logger.debug(
            "Kelly sizing | kelly=%.3f risk_cap=%.2f lots=%.2f",
            kelly_fraction,
            risk_capital,
            lot_size,
        )
        return lot_size

    def update_equity(self, current_equity: float) -> None:
        """Call after every closed trade or on heartbeat."""
        self.balance = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        if current_equity > self.daily.peak_equity:
            self.daily.peak_equity = current_equity

    def record_pnl(self, pnl: float) -> None:
        """Accumulate intraday realised PnL."""
        self.daily.realised_pnl += pnl
        self.daily.trade_count += 1

    def reset_daily(self) -> None:
        """Must be called at the start of each trading day."""
        if self.monitor:
            self.monitor.send_daily_summary(
                self.daily.realised_pnl, self.daily.trade_count
            )
        self.daily = DailyStats(peak_equity=self.balance)
        logger.info("Daily stats reset")

    # -- Private filter layers ----------------------------------------------
    def _check_circuit_breaker(self) -> bool:
        drawdown = (self.peak_equity - self.balance) / self.peak_equity
        if drawdown >= self.cfg.circuit_breaker_threshold:
            logger.critical(
                "CIRCUIT BREAKER: drawdown=%.1f%% - trading halted",
                drawdown * 100,
            )
            if self.trade_logger:
                self.trade_logger.log_risk_event(
                    event_type="CIRCUIT_BREAKER",
                    description=f"Drawdown {drawdown * 100:.1f}% hit 15% limit",
                )
            if self.monitor:
                self.monitor.alert_circuit_breaker(drawdown)
            return False
        return True

    def _check_daily_loss(self) -> bool:
        if self.daily.peak_equity == 0:
            return True
        loss_pct = abs(self.daily.realised_pnl) / self.daily.peak_equity
        if self.daily.realised_pnl < 0 and loss_pct >= self.cfg.max_daily_loss:
            logger.warning("Daily loss limit hit: %.1f%%", loss_pct * 100)
            return False
        return True

    def _check_max_positions(self) -> bool:
        if len(self.open_positions) >= self.cfg.max_positions:
            logger.debug("Max positions reached (%d)", self.cfg.max_positions)
            return False
        return True

    def _check_symbol_allocation(self, symbol: str) -> bool:
        """Block trading on symbols not in the All-Weather portfolio."""
        if symbol not in ALLOCATION_WEIGHTS:
            logger.warning("Symbol %s not in approved portfolio", symbol)
            return False
        return True

    def _check_minimum_confidence(self, confidence: float) -> bool:
        threshold = self.cfg.confidence_threshold
        if confidence < threshold:
            logger.debug(
                "Confidence %.2f below threshold %.2f", confidence, threshold
            )
            return False
        return True

    def _check_risk_reward(self, signal: TradeSignal) -> bool:
        min_rr = self.cfg.min_risk_reward
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.entry_price)
        if risk == 0:
            return False
        rr = reward / risk
        if rr < min_rr:
            logger.debug("R:R %.2f below minimum %.2f", rr, min_rr)
            return False
        return True


__all__ = ["ALLOCATION_WEIGHTS", "DailyStats", "RiskManager", "TradeSignal"]
