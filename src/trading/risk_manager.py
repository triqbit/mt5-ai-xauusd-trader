"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_manager.py

Enterprise risk management engine implementing:
  - Kelly Criterion position sizing (fractional)
  - Ray Dalio All-Weather portfolio allocation
  - Dynamic drawdown protection & circuit breakers
  - 6-layer entry filter cascade

This module relies on the unified TradeSignal schema from src.core.schemas
to ensure all signals entering the risk engine are technically valid.

Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

import pandas as pd

from src.core.config import TradingConfig
from src.core.monitor import Monitor
from src.core.schemas import TradeSignal
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
class DailyStats:
    """Intraday PnL tracker reset each trading day."""

    date: date = field(default_factory=date.today)
    realised_pnl: float = 0.0
    trade_count: int = 0
    peak_equity: float = 0.0
    consecutive_losses: int = 0


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
    def approve(
        self,
        signal: TradeSignal,
        signal_id: Optional[int] = None,
        model_health: Optional[dict] = None,
        current_positions: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """
        Run the full institutional risk filter cascade.
        Returns True only if ALL layers pass.
        """
        rejection_reason = ""
        if not self._check_circuit_breaker():
            rejection_reason = "Circuit breaker active"
        elif not self._check_daily_loss():
            rejection_reason = "Daily loss limit reached"
        elif not self._check_max_positions():
            rejection_reason = "Max concurrent positions reached"
        elif current_positions is not None and not self._check_directional_exposure(signal, current_positions):
            rejection_reason = "Max directional exposure reached"
        elif current_positions is not None and not self._check_total_notional(signal, current_positions):
            rejection_reason = "Total notional exposure limit reached"
        elif not self._check_symbol_allocation(signal.symbol):
            rejection_reason = f"Symbol {signal.symbol} not in portfolio"
        elif not self._check_minimum_confidence(signal.confidence):
            rejection_reason = f"Confidence {signal.confidence:.2f} below {self.cfg.min_confidence}"
        elif not self._check_risk_reward(signal):
            rejection_reason = "Risk-Reward ratio too low"
        elif not self._check_consecutive_losses():
            rejection_reason = "Max consecutive losses reached"
        elif not self._check_model_health(model_health):
            rejection_reason = "Model health metrics below threshold"

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

    def calculate_atr_size_multiplier(self, market_data: pd.DataFrame) -> float:
        """
        ATR-based volatility scaling multiplier.
        """
        if market_data.empty or "atr" not in market_data.columns:
            return 1.0

        current_atr = market_data["atr"].iloc[-1]
        # Approx 30 days of M5 if 24/5 trading
        avg_atr = market_data["atr"].tail(8640).mean()

        ratio = current_atr / avg_atr if avg_atr > 0 else 1.0

        if ratio > self.cfg.volatility_extreme_threshold:
            return 0.0
        elif ratio > self.cfg.volatility_very_high_threshold:
            return 0.5
        elif ratio > self.cfg.volatility_high_threshold:
            return 0.75
        return 1.0

    def size_position(
        self,
        symbol: str,
        market_data: Optional[pd.DataFrame] = None,
        win_rate: float = 0.58,
        avg_win: float = 0.0,
        avg_loss: float = 0.0,
    ) -> float:
        """
        Institutional position sizing combining Kelly and ATR-based volatility scaling.
        """
        # 1. Base Sizing (1% of balance)
        risk_amount = self.balance * self.cfg.risk_per_trade

        # 2. ATR Multiplier (Volatility Scaling)
        vol_multiplier = 1.0
        current_atr = 0.0
        if market_data is not None and not market_data.empty:
            vol_multiplier = self.calculate_atr_size_multiplier(market_data)
            current_atr = market_data["atr"].iloc[-1] if "atr" in market_data.columns else 0.0

        # 3. Daily Loss Multiplier
        loss_multiplier = self.get_size_multiplier_from_loss()

        total_multiplier = vol_multiplier * loss_multiplier
        if total_multiplier <= 0:
            return 0.0

        # 4. Calculate Lots
        if avg_loss > 0 and win_rate > 0:
            # Use Kelly Criterion if performance stats available
            kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
            kelly_fraction = max(0.0, min(kelly_fraction, 0.25))
            lot_size = (risk_amount * kelly_fraction) / avg_loss
        elif current_atr > 0:
            # Fallback to ATR-based sizing (RISK_LIMITS.md standard)
            # ATR * 100 converts gold ATR to $ per lot
            lot_size = (risk_amount / (current_atr * 100)) * total_multiplier
        else:
            # Default to minimum lot if no data
            lot_size = self.cfg.min_lot_size

        # 5. Cap at Max Position Size (10% of equity)
        max_notional = self.balance * self.cfg.max_position_size_pct
        # Price estimate for gold
        price = market_data["close"].iloc[-1] if market_data is not None and not market_data.empty else 2300.0
        max_lots = max_notional / (price * 100)

        final_lots = min(lot_size, max_lots)
        final_lots = max(self.cfg.min_lot_size, round(final_lots, 2))

        logger.debug(
            "Sizing | symbol=%s | mult=%.2f | lots=%.2f",
            symbol, total_multiplier, final_lots
        )
        return final_lots

    def update_equity(self, current_equity: float, realised_pnl: float = 0.0) -> None:
        """Call after every closed trade or on heartbeat."""
        self.balance = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        if realised_pnl != 0:
            self.daily.realised_pnl += realised_pnl
            self.daily.trade_count += 1
            if realised_pnl < 0:
                self.daily.consecutive_losses += 1
            else:
                self.daily.consecutive_losses = 0

        if current_equity > self.daily.peak_equity:
            self.daily.peak_equity = current_equity

    def record_pnl(self, pnl: float) -> None:
        """Accumulate intraday realised PnL."""
        self.daily.realised_pnl += pnl
        self.daily.trade_count += 1
        if pnl < 0:
            self.daily.consecutive_losses += 1
        else:
            self.daily.consecutive_losses = 0

    def get_daily_loss_level(self) -> int:
        """
        Layer 2: Daily Loss Level (0-4).
        """
        if self.daily.peak_equity <= 0 or self.daily.realised_pnl >= 0:
            return 0

        loss_pct = abs(self.daily.realised_pnl) / self.daily.peak_equity

        if loss_pct >= self.cfg.max_daily_loss:
            return 4
        if loss_pct >= self.cfg.daily_loss_lvl3:
            return 3
        if loss_pct >= self.cfg.daily_loss_lvl2:
            return 2
        if loss_pct >= self.cfg.daily_loss_lvl1:
            return 1
        return 0

    def get_size_multiplier_from_loss(self) -> float:
        """Multiplier based on daily loss level."""
        level = self.get_daily_loss_level()
        mapping = {0: 1.0, 1: 1.0, 2: 0.5, 3: 0.25, 4: 0.0}
        return mapping.get(level, 0.0)

    def reset_daily(self) -> None:
        """Must be called at the start of each trading day."""
        if self.monitor:
            self.monitor.send_daily_summary(self.daily.realised_pnl, self.daily.trade_count)
        self.daily = DailyStats(peak_equity=self.balance)
        logger.info("Daily stats reset")

    # -- Private filter layers ----------------------------------------------
    def _check_consecutive_losses(self) -> bool:
        if self.daily.consecutive_losses >= self.cfg.max_losing_streak:
            logger.warning(
                "Losing streak limit hit: %d (Limit: %d)",
                self.daily.consecutive_losses,
                self.cfg.max_losing_streak,
            )
            return False
        return True

    def _check_model_health(self, health: Optional[dict]) -> bool:
        if health is None:
            return True

        drift = float(health.get("drift", 0.0))
        accuracy = float(health.get("accuracy", 1.0))
        calibration = float(health.get("calibration", 0.0))

        if drift > self.cfg.model_drift_threshold:
            logger.warning(
                "Model drift too high: %.2f > %.2f", drift, self.cfg.model_drift_threshold
            )
            return False
        if accuracy < self.cfg.model_accuracy_floor:
            logger.warning(
                "Model accuracy too low: %.2f < %.2f", accuracy, self.cfg.model_accuracy_floor
            )
            return False
        if calibration > self.cfg.model_calibration_threshold:
            logger.warning(
                "Model calibration error too high: %.2f > %.2f",
                calibration,
                self.cfg.model_calibration_threshold,
            )
            return False

        return True

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
        level = self.get_daily_loss_level()
        if level >= 4:
            logger.warning("Daily loss limit hit (Level 4)")
            return False
        return True

    def _check_directional_exposure(
        self, signal: TradeSignal, current_positions: List[Dict[str, Any]]
    ) -> bool:
        """Layer 4: 30% net directional exposure."""
        net_lots = 0.0
        for pos in current_positions:
            vol = pos.get("volume", 0.0)
            if pos.get("type") == 0:  # BUY
                net_lots += vol
            else:  # SELL
                net_lots -= vol

        # Factor in the new signal
        net_lots += self.cfg.min_lot_size if signal.direction > 0 else -self.cfg.min_lot_size

        # Gold price estimate for notional calculation if not available via market data
        price_estimate = signal.entry_price or 2300.0
        notional = abs(net_lots) * price_estimate * 100
        exposure_pct = notional / self.balance if self.balance > 0 else 1.0

        if exposure_pct > self.cfg.max_single_direction_pct:
            logger.warning("Max directional exposure reached: %.1f%%", exposure_pct * 100)
            return False
        return True

    def _check_total_notional(
        self, signal: TradeSignal, current_positions: List[Dict[str, Any]]
    ) -> bool:
        """Layer 4: Total notional < 100% equity."""
        total_lots = sum(pos.get("volume", 0.0) for pos in current_positions) + self.cfg.min_lot_size
        price = signal.entry_price or 2300.0
        total_notional = total_lots * price * 100
        limit = self.balance * self.cfg.max_total_notional_pct
        if total_notional >= limit:
            logger.warning("Total notional exposure exceeds equity: %.1f >= %.1f", total_notional, limit)
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


__all__ = ["ALLOCATION_WEIGHTS", "DailyStats", "RiskManager"]
