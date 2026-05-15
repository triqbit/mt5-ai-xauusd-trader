"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_manager.py

Enterprise risk management engine implementing:
  - Kelly Criterion position sizing (fractional)
  - ATR-based position sizing (14-period vs 30-day average)
  - Ray Dalio All-Weather portfolio allocation
  - Dynamic drawdown protection & circuit breakers
  - 8-layer safety cascade signal validation

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
from src.core.constants import SignalDirection
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
class RiskDecision:
    """Decision details from the Risk Manager."""

    is_approved: bool
    reason: str = ""
    adjusted_lot_size: float = 0.0


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

    def validate_signal(
        self,
        signal: TradeSignal,
        market_data: pd.DataFrame,
        open_positions: List[Dict[str, Any]],
        model_health: Optional[Dict[str, float]] = None,
    ) -> RiskDecision:
        """
        Validate a trade signal against the 8-layer cascade from RISK_LIMITS.md.

        Layers:
          1. Circuit Breakers (Equity Drawdown).
          2. Daily Loss Limits (Level 4 Emergency Stop).
          3. Activity Limits (Max Daily Trades, Max Consecutive Losses).
          4. Exposure Limits (Max Concurrent Positions, Single Direction, Total Notional).
          5. Symbol Allocation (Approved Portfolio).
          6. Prediction Limits (Min Confidence).
          7. Risk-Reward Validation (Institutional R:R ratio).
          8. Model Health (Drift, Accuracy, Calibration).
        """
        # Layer 1: Circuit Breakers (Equity Drawdown)
        if not self._check_drawdown_breaker():
            return RiskDecision(False, "Hard drawdown limit reached")

        # Layer 2: Daily Loss Limits
        if self.get_daily_loss_level() >= 4:
            return RiskDecision(False, "Daily loss limit reached (Level 4)")

        # Layer 3: Activity Limits
        if self.daily.trade_count >= self.cfg.max_trades_per_day:
            return RiskDecision(False, "Max daily trades reached")
        if self.daily.consecutive_losses >= self.cfg.max_losing_streak:
            return RiskDecision(False, "Max consecutive losses reached")

        # Layer 4: Exposure Limits
        if len(open_positions) >= self.cfg.max_positions:
            return RiskDecision(False, "Max concurrent positions reached")
        if not self._check_directional_exposure(signal, open_positions):
            return RiskDecision(False, "Max directional exposure reached (30%)")
        if not self._check_total_notional(signal, open_positions, market_data):
            return RiskDecision(False, "Total notional exposure exceeds equity")

        # Layer 5: Symbol Allocation
        if not self._check_symbol_allocation(signal.symbol):
            return RiskDecision(False, f"Symbol {signal.symbol} not in approved portfolio")

        # Layer 6: Prediction Limits
        if not self._check_minimum_confidence(signal.confidence):
            return RiskDecision(
                False, f"Confidence {signal.confidence:.2f} below {self.cfg.min_confidence}"
            )

        # Layer 7: Risk-Reward Validation (Min 1.5 R:R)
        if not self._check_risk_reward(signal):
            return RiskDecision(False, "Risk-Reward ratio below 1.5")

        # Layer 8: Model Health
        if not self._check_model_health(model_health):
            return RiskDecision(False, "Model health metrics below threshold")

        # Calculate final lot size using ATR-based sizing
        adjusted_lots = self.size_position(signal.symbol, market_data=market_data)

        if adjusted_lots < self.cfg.min_lot_size:
            return RiskDecision(False, f"Calculated lot size {adjusted_lots} below minimum")

        return RiskDecision(True, "Approved", adjusted_lots)

    def approve(
        self,
        signal: TradeSignal,
        signal_id: Optional[int] = None,
        model_health: Optional[dict] = None,
    ) -> bool:
        """
        Legacy compatibility wrapper for validate_signal.
        Used by main.py live loop.
        """
        rejection_reason = ""
        if not self._check_drawdown_breaker():
            rejection_reason = "Circuit breaker active"
        elif self.get_daily_loss_level() >= 4:
            rejection_reason = "Daily loss limit reached"
        elif len(self.open_positions) >= self.cfg.max_positions:
            rejection_reason = "Max positions reached"
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
        market_data: Optional[pd.DataFrame] = None,
        win_rate: Optional[float] = None,
        avg_win: Optional[float] = None,
        avg_loss: Optional[float] = None,
        pip_value: float = 1.0,
    ) -> float:
        """
        Dual-mode position sizing:
        1. ATR-based (Institutional) if market_data is DataFrame.
        2. Fractional Kelly (Legacy) if parameters are provided.
        """
        if isinstance(market_data, pd.DataFrame):
            return self._calculate_atr_size(symbol, market_data)

        if win_rate is not None and avg_win is not None and avg_loss is not None:
             return self._calculate_kelly_size(win_rate, avg_win, avg_loss, pip_value)

        return self.cfg.min_lot_size

    def _calculate_kelly_size(self, win_rate: float, avg_win: float, avg_loss: float, pip_value: float) -> float:
        """Fractional Kelly Criterion position sizing."""
        if avg_loss == 0:
            return self.cfg.min_lot_size
        kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        kelly_fraction = max(0.0, min(kelly_fraction, 0.25))  # cap at 25% Kelly
        risk_capital = self.balance * self.cfg.risk_per_trade
        lot_size = (risk_capital * kelly_fraction) / (avg_loss * pip_value)
        lot_size = max(self.cfg.min_lot_size, round(lot_size, 2))
        logger.debug(
            "Kelly sizing | kelly=%.3f risk_cap=%.2f lots=%.2f",
            kelly_fraction,
            risk_capital,
            lot_size,
        )
        return lot_size

    def _calculate_atr_size(self, symbol: str, market_data: pd.DataFrame) -> float:
        """ATR-based position sizing logic from RiskEngine."""
        if market_data.empty or "atr" not in market_data.columns:
            return self.cfg.min_lot_size

        current_atr = market_data["atr"].iloc[-1]
        avg_atr = market_data["atr"].tail(8640).mean()  # Approx 30 days of M5

        vol_multiplier = 1.0
        ratio = current_atr / avg_atr if avg_atr > 0 else 1.0

        if ratio > self.cfg.volatility_extreme_threshold:
            return 0.0
        elif ratio > self.cfg.volatility_very_high_threshold:
            vol_multiplier = 0.5
        elif ratio > self.cfg.volatility_high_threshold:
            vol_multiplier = 0.75

        loss_multiplier = self.get_size_multiplier_from_loss()
        total_multiplier = vol_multiplier * loss_multiplier

        if total_multiplier <= 0:
            return 0.0

        risk_amount = self.balance * self.cfg.risk_per_trade
        # ATR * 100 converts gold ATR to $ per lot (1.0 ATR move = $100 per lot)
        lot_size = (risk_amount / (current_atr * 100)) * total_multiplier

        # Cap at Max Position Size (10% of equity)
        max_notional = self.balance * self.cfg.max_position_size_pct
        price = market_data["close"].iloc[-1] if "close" in market_data.columns else 2300.0
        max_lots = max_notional / (price * 100)

        final_lots = min(lot_size, max_lots)
        final_lots = max(self.cfg.min_lot_size, round(final_lots, 2))

        return final_lots

    def update_equity(self, current_equity: float) -> None:
        """Update equity trackers and daily stats."""
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

    # -- Internal cascade layers -------------------------------------------

    def _check_drawdown_breaker(self) -> bool:
        """Layer 1: Equity Drawdown."""
        if self.peak_equity <= 0:
            return True
        drawdown = (self.peak_equity - self.balance) / self.peak_equity
        if drawdown >= self.cfg.max_drawdown:
            logger.critical("CIRCUIT BREAKER: Drawdown %.2f%% hit limit", drawdown * 100)
            if self.trade_logger:
                self.trade_logger.log_risk_event(
                    event_type="CIRCUIT_BREAKER",
                    description=f"Drawdown {drawdown * 100:.1f}% hit limit",
                )
            if self.monitor:
                self.monitor.alert_circuit_breaker(drawdown)
            return False
        return True

    def get_daily_loss_level(self) -> int:
        """Layer 2: Daily Loss Level (0-4)."""
        if self.daily.peak_equity <= 0 or self.daily.realised_pnl >= 0:
            return 0
        loss_pct = abs(self.daily.realised_pnl) / self.daily.peak_equity
        if loss_pct >= self.cfg.max_daily_loss: return 4
        if loss_pct >= self.cfg.daily_loss_lvl3: return 3
        if loss_pct >= self.cfg.daily_loss_lvl2: return 2
        if loss_pct >= self.cfg.daily_loss_lvl1: return 1
        return 0

    def get_size_multiplier_from_loss(self) -> float:
        level = self.get_daily_loss_level()
        mapping = {0: 1.0, 1: 1.0, 2: 0.5, 3: 0.25, 4: 0.0}
        return mapping.get(level, 0.0)

    def _check_consecutive_losses(self) -> bool:
        return self.daily.consecutive_losses < self.cfg.max_losing_streak

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

        # SignalDirection is IntEnum, so comparison works
        net_lots += self.cfg.min_lot_size if signal.direction == SignalDirection.BUY else -self.cfg.min_lot_size
        price_estimate = 2300.0  # Gold estimate
        notional = abs(net_lots) * price_estimate * 100
        exposure_pct = notional / self.balance if self.balance > 0 else 1.0
        return exposure_pct <= self.cfg.max_single_direction_pct

    def _check_total_notional(
        self, signal: TradeSignal, open_positions: List[Dict[str, Any]], market_data: pd.DataFrame
    ) -> bool:
        """Layer 4: Total notional < 100% equity."""
        total_lots = sum(pos.get("volume", 0.0) for pos in open_positions) + self.cfg.min_lot_size
        price = market_data["close"].iloc[-1] if not market_data.empty else 2300.0
        total_notional = total_lots * price * 100
        return total_notional < (self.balance * self.cfg.max_total_notional_pct)

    def _check_symbol_allocation(self, symbol: str) -> bool:
        return symbol in ALLOCATION_WEIGHTS or symbol == self.cfg.symbol

    def _check_minimum_confidence(self, confidence: float) -> bool:
        return confidence >= self.cfg.min_confidence

    def _check_risk_reward(self, signal: TradeSignal, min_rr: float = 1.5) -> bool:
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.entry_price)
        return reward >= (risk * min_rr) if risk > 0 else False

    def _check_model_health(self, health: Optional[Dict[str, float]]) -> bool:
        if health is None:
            return True
        if health.get("drift", 0.0) > self.cfg.model_drift_threshold:
            return False
        if health.get("accuracy", 1.0) < self.cfg.model_accuracy_floor:
            return False
        return health.get("calibration", 0.0) <= self.cfg.model_calibration_threshold


__all__ = ["ALLOCATION_WEIGHTS", "DailyStats", "RiskDecision", "RiskManager"]
