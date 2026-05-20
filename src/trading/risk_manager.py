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
        market_data: Optional[pd.DataFrame] = None,
        open_positions: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """
        Run the full 8-layer risk filter cascade.
        Returns True only if ALL layers pass.
        """
        rejection_reason = ""
        if not self._check_circuit_breaker():
            rejection_reason = "Circuit breaker active"
        elif not self._check_daily_loss():
            rejection_reason = "Daily loss limit reached"
        elif not self._check_max_positions():
            rejection_reason = "Max positions reached"
        elif open_positions is not None and not self._check_directional_exposure(
            signal, open_positions
        ):
            rejection_reason = "Max directional exposure reached"
        elif (
            open_positions is not None
            and market_data is not None
            and not self._check_total_notional(signal, open_positions, market_data)
        ):
            rejection_reason = "Total notional exposure exceeds limit"
        elif not self._check_symbol_allocation(signal.symbol):
            rejection_reason = f"Symbol {signal.symbol} not in portfolio"
        elif not self._check_minimum_confidence(signal.confidence):
            rejection_reason = f"Confidence {signal.confidence:.2f} too low"
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

    def size_position_atr(self, symbol: str, market_data: pd.DataFrame) -> float:
        """
        ATR-based position sizing according to RISK_LIMITS.md.

        Logic:
          - Compare 14-period ATR to 30-day average.
          - Normal Volatility: 100% position size.
          - High Volatility (>1.5x): Reduce to 75% position size.
          - Very High Volatility (>2x): Reduce to 50% position size.
          - Extreme Volatility (>3x): HALT (0.0 lots).

        Additional Constraints:
          - Daily loss level multiplier (100%, 50%, 25%, 0%).
          - Max Position Size (10% of account equity per trade).
        """
        if market_data.empty or "atr" not in market_data.columns:
            return self.cfg.min_lot_size

        current_atr = market_data["atr"].iloc[-1]
        avg_atr = market_data["atr"].tail(8640).mean()  # Approx 30 days of M5

        vol_multiplier = 1.0
        ratio = current_atr / avg_atr if avg_atr > 0 else 1.0

        if ratio > getattr(self.cfg, "volatility_extreme_threshold", 3.0):
            return 0.0
        elif ratio > getattr(self.cfg, "volatility_very_high_threshold", 2.0):
            vol_multiplier = 0.5
        elif ratio > getattr(self.cfg, "volatility_high_threshold", 1.5):
            vol_multiplier = 0.75

        # Multiplier based on daily loss level
        loss_pct = (
            abs(self.daily.realised_pnl) / self.daily.peak_equity
            if self.daily.peak_equity > 0
            else 0
        )
        level = 0
        if self.daily.realised_pnl < 0:
            if loss_pct >= self.cfg.max_daily_loss:
                level = 4
            elif loss_pct >= getattr(self.cfg, "daily_loss_lvl3", 0.05):
                level = 3
            elif loss_pct >= getattr(self.cfg, "daily_loss_lvl2", 0.03):
                level = 2
            elif loss_pct >= getattr(self.cfg, "daily_loss_lvl1", 0.01):
                level = 1

        mapping = {0: 1.0, 1: 1.0, 2: 0.5, 3: 0.25, 4: 0.0}
        loss_multiplier = mapping.get(level, 0.0)
        total_multiplier = vol_multiplier * loss_multiplier

        if total_multiplier <= 0:
            return 0.0

        # Sizing: risk 1% (cfg.risk_per_trade) of balance
        risk_amount = self.balance * self.cfg.risk_per_trade
        # ATR * 100 converts gold ATR to $ per lot
        lot_size = (risk_amount / (current_atr * 100)) * total_multiplier

        # Cap at Max Position Size (10% of equity)
        max_notional = self.balance * getattr(self.cfg, "max_position_size_pct", 0.1)
        price = market_data["close"].iloc[-1]
        max_lots = max_notional / (price * 100)

        final_lots = min(lot_size, max_lots)
        final_lots = max(self.cfg.min_lot_size, round(final_lots, 2))

        return final_lots

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
        if pnl < 0:
            self.daily.consecutive_losses += 1
        else:
            self.daily.consecutive_losses = 0

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

    def _check_directional_exposure(
        self, signal: TradeSignal, open_positions: List[Dict[str, Any]]
    ) -> bool:
        """Layer 4: 30% net directional exposure."""
        net_lots = 0.0
        for pos in open_positions:
            vol = pos.get("volume", 0.0)
            if pos.get("type") == 0:  # BUY
                net_lots += vol
            else:  # SELL
                net_lots -= vol

        net_lots += self.cfg.min_lot_size if signal.direction > 0 else -self.cfg.min_lot_size
        price_estimate = 2300.0  # Gold estimate
        notional = abs(net_lots) * price_estimate * 100
        exposure_pct = notional / self.balance if self.balance > 0 else 1.0

        limit = getattr(self.cfg, "max_single_direction_pct", 0.3)
        return exposure_pct <= limit

    def _check_total_notional(
        self, signal: TradeSignal, open_positions: List[Dict[str, Any]], market_data: pd.DataFrame
    ) -> bool:
        """Layer 4: Total notional < 100% equity."""
        total_lots = sum(pos.get("volume", 0.0) for pos in open_positions) + self.cfg.min_lot_size
        price = market_data["close"].iloc[-1] if not market_data.empty else 2300.0
        total_notional = total_lots * price * 100
        limit = getattr(self.cfg, "max_total_notional_pct", 1.0)
        return total_notional < (self.balance * limit)


__all__ = ["ALLOCATION_WEIGHTS", "DailyStats", "RiskManager"]
