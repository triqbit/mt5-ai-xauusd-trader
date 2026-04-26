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
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


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
        self.atr_baseline: Optional[float] = None
        logger.info("RiskManager initialised | balance=%.2f", account_balance)

    # -- Public API ---------------------------------------------------------
    def approve(self, signal: TradeSignal, signal_id: Optional[int] = None) -> bool:
        """
        Run the full risk filter cascade.
        Returns True only if ALL layers pass.
        """
        rejection_reason = ""
        if not self._check_circuit_breaker():
            rejection_reason = "Circuit breaker active"
        elif not self._check_daily_loss():
            rejection_reason = "Daily loss limit reached (Level 4 HALT)"
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
        current_atr: Optional[float] = None,
    ) -> float:
        """
        Fractional Kelly Criterion position sizing with risk scaling.
        """
        if avg_loss == 0:
            return 0.01  # minimum lot

        # 1. Base Kelly sizing
        kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        kelly_fraction = max(0.0, min(kelly_fraction, 0.25))  # cap at 25% Kelly

        # 2. Daily Loss Cascading Scale
        loss_scale = self._get_daily_loss_scale()

        # 3. Volatility Scale
        vol_scale = self._get_volatility_scale(current_atr)

        # Combined scaling
        effective_scale = loss_scale * vol_scale

        risk_capital = self.balance * self.cfg.risk_per_trade * effective_scale
        lot_size = (risk_capital * kelly_fraction) / (avg_loss * pip_value)
        lot_size = max(0.01, round(lot_size, 2))

        logger.debug(
            "Sizing | scale=%.2f (loss=%.2f, vol=%.2f) kelly=%.3f lots=%.2f",
            effective_scale, loss_scale, vol_scale, kelly_fraction, lot_size
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

    def update_atr_baseline(self, baseline: float) -> None:
        """Update the 30-day ATR baseline for volatility scaling."""
        self.atr_baseline = baseline

    # -- Private filter layers ----------------------------------------------
    def _get_daily_loss_scale(self) -> float:
        """
        Level 1 (2% loss) -> Alert (scale 1.0)
        Level 2 (3% loss) -> 50% size
        Level 3 (4% loss) -> 25% size
        Level 4 (5% loss) -> HALT (scale 0.0)
        """
        if self.daily.peak_equity == 0:
            return 1.0

        loss_pct = abs(self.daily.realised_pnl) / self.daily.peak_equity
        if self.daily.realised_pnl >= 0:
            return 1.0

        if loss_pct >= 0.05:
            return 0.0
        if loss_pct >= 0.04:
            return 0.25
        if loss_pct >= 0.03:
            return 0.50
        if loss_pct >= 0.02:
            logger.warning("Daily Loss Level 1 (2%%) hit - Alerting")
            return 1.0
        return 1.0

    def _get_volatility_scale(self, current_atr: Optional[float]) -> float:
        """
        Normal Volatility: 1.0
        High Volatility (>1.5x): 0.75
        Very High Volatility (>2.0x): 0.50
        Extreme Volatility (>3.0x): 0.0 (HALT)
        """
        if current_atr is None or self.atr_baseline is None or self.atr_baseline == 0:
            return 1.0

        ratio = current_atr / self.atr_baseline
        if ratio >= 3.0:
            return 0.0
        if ratio >= 2.0:
            return 0.50
        if ratio >= 1.5:
            return 0.75
        return 1.0

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
        return self._get_daily_loss_scale() > 0

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

    def _check_minimum_confidence(
        self, confidence: float, threshold: float = 0.55
    ) -> bool:
        if confidence < threshold:
            logger.debug(
                "Confidence %.2f below threshold %.2f", confidence, threshold
            )
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


__all__ = ["ALLOCATION_WEIGHTS", "DailyStats", "RiskManager", "TradeSignal"]
