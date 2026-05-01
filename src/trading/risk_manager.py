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
from datetime import date, datetime
from typing import Dict, List, Optional

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
        reasons = self._get_rejection_reason(signal)
        passed = len(reasons) == 0

        if not passed:
            rejection_reason = reasons[0]
            logger.warning(
                "Signal REJECTED | %s %s | Reason: %s",
                signal.symbol,
                signal.direction,
                rejection_reason,
            )

            # Critical alerts and logging
            if "Circuit breaker" in rejection_reason:
                drawdown = (self.peak_equity - self.balance) / self.peak_equity
                if self.monitor:
                    self.monitor.alert_circuit_breaker(drawdown)
                if self.trade_logger:
                    self.trade_logger.log_risk_event(
                        event_type="CIRCUIT_BREAKER",
                        description=rejection_reason,
                        symbol=signal.symbol,
                        signal_id=signal_id,
                    )

            if self.trade_logger:
                self.trade_logger.log_risk_event(
                    event_type="SIGNAL_REJECTED",
                    description="; ".join(reasons),
                    symbol=signal.symbol,
                    signal_id=signal_id,
                )
        return passed

    def _get_rejection_reason(self, signal: TradeSignal) -> List[str]:
        """
        Evaluate all risk filters and return a list of rejection reasons.
        Side-effect free (no logging or state changes).
        """
        reasons = []

        checks = [
            self._check_circuit_breaker(),
            self._check_daily_loss(),
            self._check_max_positions(),
            self._check_symbol_allocation(signal.symbol),
            self._check_minimum_confidence(signal.confidence),
            self._check_risk_reward(signal),
        ]

        for reason in checks:
            if reason:
                reasons.append(reason)

        return reasons

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

    # -- Private filter layers (Side-effect free) --------------------------
    def _check_circuit_breaker(self) -> Optional[str]:
        drawdown = (self.peak_equity - self.balance) / self.peak_equity
        if drawdown >= 0.15:  # 15% peak-to-valley kills all trading
            return f"Circuit breaker active (drawdown {drawdown:.1%})"
        return None

    def _check_daily_loss(self) -> Optional[str]:
        if self.daily.peak_equity <= 0:
            return None
        loss_pct = abs(self.daily.realised_pnl) / self.daily.peak_equity
        if self.daily.realised_pnl < 0 and loss_pct >= self.cfg.max_daily_loss:
            return f"Daily loss limit reached ({loss_pct:.1%})"
        return None

    def _check_max_positions(self) -> Optional[str]:
        if len(self.open_positions) >= self.cfg.max_positions:
            return f"Max positions reached ({self.cfg.max_positions})"
        return None

    def _check_symbol_allocation(self, symbol: str) -> Optional[str]:
        """Block trading on symbols not in the All-Weather portfolio."""
        if symbol not in ALLOCATION_WEIGHTS:
            return f"Symbol {symbol} not in approved portfolio"
        return None

    def _check_minimum_confidence(
        self, confidence: float
    ) -> Optional[str]:
        threshold = getattr(self.cfg, "confidence_threshold", 0.55)
        if confidence < threshold:
            return f"Confidence {confidence:.2f} below threshold {threshold:.2f}"
        return None

    def _check_risk_reward(self, signal: TradeSignal) -> Optional[str]:
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.entry_price)
        min_rr = 1.5
        if risk == 0:
            return "Invalid risk (SL=Entry)"
        rr = reward / risk
        if rr < min_rr:
            return f"Risk-Reward ratio {rr:.2f} below minimum {min_rr:.2f}"
        return None


__all__ = ["ALLOCATION_WEIGHTS", "DailyStats", "RiskManager", "TradeSignal"]
