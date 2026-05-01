"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_manager.py
Enterprise risk management engine implementing:
  - Kelly Criterion position sizing (fractional)
  - Ray Dalio All-Weather portfolio allocation
  - Dynamic drawdown protection & circuit breakers
  - 8-layer entry filter cascade
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Dict, Optional

import pandas as pd

from src.core.config import TradingConfig
from src.core.monitor import Monitor
from src.core.trade_logger import TradeLogger
from src.trading.execution_filter import ExecutionFilter
from src.data.event_intelligence import EventIntelligence

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
    confidence: float


@dataclass
class DailyStats:
    """Intraday performance tracking."""

    realised_pnl: float = 0.0
    trade_count: int = 0
    peak_equity: float = 0.0


class RiskManager:
    """
    Orchestrates capital allocation, position sizing, and risk gates.
    """

    def __init__(
        self,
        cfg: TradingConfig,
        account_balance: float,
        logger_db: Optional[TradeLogger] = None,
        monitor: Optional[Monitor] = None,
        execution_filter: Optional[ExecutionFilter] = None,
        event_intel: Optional[EventIntelligence] = None,
    ) -> None:
        self.cfg = cfg
        self.balance = account_balance
        self.peak_equity = account_balance
        self.trade_logger = logger_db
        self.monitor = monitor
        self.execution_filter = execution_filter or ExecutionFilter()
        self.event_intel = event_intel
        self.daily = DailyStats(peak_equity=account_balance)
        self.open_positions: Dict[str, int] = {}  # symbol -> ticket
        logger.info("RiskManager initialised | balance=%.2f", account_balance)

    def approve(
        self,
        signal: TradeSignal,
        signal_id: Optional[int] = None,
        market_data: Optional[pd.DataFrame] = None,
        current_spread: float = 0.0,
    ) -> bool:
        """
        Run the full 8-layer risk and execution filter cascade.
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
        elif not self._check_macro_events(signal.symbol):
            rejection_reason = "Macro event risk"

        # Technical Execution Filter Layer
        if not rejection_reason and market_data is not None:
            drawdown = (self.peak_equity - self.balance) / self.peak_equity
            decision = self.execution_filter.validate(
                signal, market_data, drawdown, current_spread
            )
            if not decision.is_approved:
                rejection_reason = decision.blocked_by or "Technical Filter rejection"

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
    ) -> float:
        """
        Kelly Criterion sizing: f = p - (1-p) / (win/loss)
        """
        if avg_loss == 0:
            return 0.01
        p = win_rate
        b = avg_win / avg_loss
        kelly_fraction = p - (1 - p) / b

        # Apply safety constraints
        fraction = max(0, min(kelly_fraction, self.cfg.max_kelly_fraction))
        risk_capital = self.balance * fraction * self.cfg.risk_per_trade

        # Convert to lots (simple 100k unit assumption for demo)
        lot_size = round(max(risk_capital / 100, 0.01), 2)

        # Macro scaling
        if self.event_intel:
            scale = self.event_intel.get_risk_multiplier(symbol, datetime.now(timezone.utc))
            lot_size = round(lot_size * scale, 2)

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
            self.monitor.send_daily_summary(self.daily.realised_pnl, self.daily.trade_count)
        self.daily = DailyStats(peak_equity=self.balance)
        logger.info("Daily stats reset")

    # -- Private filter layers ----------------------------------------------
    def _check_circuit_breaker(self) -> bool:
        drawdown = (self.peak_equity - self.balance) / self.peak_equity
        if drawdown >= 0.15:  # 15% peak-to-valley kills all trading
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

    def _check_minimum_confidence(self, confidence: float, threshold: float = 0.55) -> bool:
        if confidence < threshold:
            logger.debug("Confidence %.2f below threshold %.2f", confidence, threshold)
            return False
        return True

    def _check_risk_reward(self, signal: TradeSignal, min_rr: float = 1.5) -> bool:
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.entry_price)
        if risk == 0:
            return False
        rr = reward / risk
        if rr < min_rr:
            logger.debug("R:R %.2f below minimum %.2f", rr, min_rr)
            return False
        return True

    def _check_macro_events(self, symbol: str) -> bool:
        """Check if high-impact macro events block execution."""
        if not self.event_intel or not self.cfg.enable_macro_filter:
            return True

        if self.event_intel.should_block_execution(symbol, datetime.now(timezone.utc)):
            logger.warning("Macro event filter blocked signal for %s", symbol)
            return False
        return True


__all__ = ["ALLOCATION_WEIGHTS", "DailyStats", "RiskManager", "TradeSignal"]
