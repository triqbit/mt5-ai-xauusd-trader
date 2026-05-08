"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_manager.py

Enterprise risk management engine implementing:
  - ATR-based position sizing (Institutional)
  - Kelly Criterion position sizing (Fractional)
  - Cascading daily loss circuit breakers (Level 1-4)
  - 8-layer safety cascade signal validation
  - Exposure limits (Directional & Notional)

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

# Ray Dalio All-Weather allocation weights (Institutional baseline)
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


@dataclass
class RiskDecision:
    """Decision details from the RiskManager."""

    is_approved: bool
    reason: str = ""
    adjusted_lot_size: float = 0.0


class RiskManager:
    """
    Central risk authority.
    Consolidates core and institutional risk logic into a single 8-layer cascade.
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
        self.open_positions: Dict[str, Any] = {}  # symbol -> ticket OR position info
        self.trade_logger = logger_db
        self.monitor = monitor
        logger.info("RiskManager initialised | balance=%.2f", account_balance)

    def validate_signal(
        self,
        signal: TradeSignal,
        market_data: Optional[pd.DataFrame] = None,
        open_positions: Optional[List[Dict[str, Any]]] = None,
        model_health: Optional[Dict[str, float]] = None,
    ) -> RiskDecision:
        """
        Validate a trade signal against the 8-layer institutional cascade.
        """
        # Layer 1: Circuit Breakers (Equity Drawdown)
        if not self._check_circuit_breaker():
            return RiskDecision(False, "Hard drawdown limit reached")

        # Layer 2: Daily Loss Limits (Level 4)
        if self.get_daily_loss_level() >= 4:
            return RiskDecision(False, "Daily loss limit reached (Level 4)")

        # Layer 3: Activity Limits
        if self.daily.trade_count >= self.cfg.max_trades_per_day:
            return RiskDecision(False, "Max daily trades reached")
        if not self._check_consecutive_losses():
            return RiskDecision(False, "Max consecutive losses reached")

        # Layer 4: Exposure Limits
        if len(self.open_positions) >= self.cfg.max_positions:
            return RiskDecision(False, "Max concurrent positions reached")
        if open_positions is not None and not self._check_directional_exposure(signal, open_positions):
            return RiskDecision(False, "Max directional exposure reached (30%)")
        if open_positions is not None and market_data is not None and not self._check_total_notional(signal, open_positions, market_data):
            return RiskDecision(False, "Total notional exposure exceeds limit")

        # Layer 5: Symbol Allocation
        if not self._check_symbol_allocation(signal.symbol):
            return RiskDecision(False, f"Symbol {signal.symbol} not in approved list")

        # Layer 6: Prediction Limits
        if not self._check_minimum_confidence(signal.confidence):
            return RiskDecision(False, f"Confidence {signal.confidence:.2f} too low")

        # Layer 7: Risk-Reward Validation (Institutional R:R)
        if not self._check_risk_reward(signal):
            return RiskDecision(False, "Risk-Reward ratio below 1.5")

        # Layer 8: Model Health
        if not self._check_model_health(model_health):
            return RiskDecision(False, "Model health metrics below threshold")

        # Calculate adjusted lot size
        adjusted_lots = self.size_position(signal.symbol, market_data=market_data, method="atr")
        if adjusted_lots < self.cfg.min_lot_size:
            return RiskDecision(False, f"Calculated lot size {adjusted_lots} below minimum")

        return RiskDecision(True, "Approved", adjusted_lots)

    def approve(
        self,
        signal: TradeSignal,
        signal_id: Optional[int] = None,
        model_health: Optional[dict] = None,
        market_data: Optional[pd.DataFrame] = None,
        open_positions_info: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """
        Run the full 8-layer risk filter cascade.
        Returns True only if ALL layers pass.
        """
        decision = self.validate_signal(
            signal=signal,
            market_data=market_data,
            open_positions=open_positions_info,
            model_health=model_health
        )

        if not decision.is_approved:
            logger.warning(
                "Signal REJECTED | %s %s | Reason: %s",
                signal.symbol,
                signal.direction,
                decision.reason,
            )
            if self.trade_logger:
                self.trade_logger.log_risk_event(
                    event_type="SIGNAL_REJECTED",
                    description=decision.reason,
                    symbol=signal.symbol,
                    signal_id=signal_id,
                )
        return decision.is_approved

    def size_position(
        self,
        symbol: str,
        win_rate: float = 0.55,
        avg_win: float = 0.0,
        avg_loss: float = 0.0,
        pip_value: float = 100.0,  # Default for Gold (100.0 per lot per full point)
        market_data: Optional[pd.DataFrame] = None,
        method: str = "atr",
    ) -> float:
        """
        Position sizing router. Supports ATR-based or Kelly sizing.
        """
        if method == "atr" and market_data is not None:
            return self._calculate_atr_sizing(symbol, market_data)

        # Fallback to Kelly or simple fractional risk
        return self._calculate_kelly_sizing(win_rate, avg_win, avg_loss, pip_value)

    def update_equity(self, current_equity: float, realized_pnl: float = 0) -> None:
        """Update balance and peak equity trackers."""
        self.balance = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        if realized_pnl != 0:
            self.record_pnl(realized_pnl)

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
        """Reset daily stats at the start of a new trading day."""
        if self.monitor:
            self.monitor.send_daily_summary(self.daily.realised_pnl, self.daily.trade_count)
        self.daily = DailyStats(peak_equity=self.balance)
        logger.info("Daily stats reset")

    def get_daily_loss_level(self) -> int:
        """Layer 2: Daily Loss Level (0-4) based on RISK_LIMITS.md."""
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

    # -- Internal sizing methods -------------------------------------------

    def _calculate_atr_sizing(self, symbol: str, market_data: pd.DataFrame) -> float:
        """ATR-based sizing logic from RiskEngine."""
        if market_data.empty or "atr" not in market_data.columns:
            return self.cfg.min_lot_size

        current_atr = market_data["atr"].iloc[-1]
        # Approx 30 days of M5 data (8640 bars) if available
        avg_atr = market_data["atr"].tail(8640).mean()

        vol_multiplier = 1.0
        ratio = current_atr / avg_atr if avg_atr > 0 else 1.0

        if ratio > self.cfg.volatility_extreme_threshold:
            return 0.0
        elif ratio > self.cfg.volatility_very_high_threshold:
            vol_multiplier = 0.5
        elif ratio > self.cfg.volatility_high_threshold:
            vol_multiplier = 0.75

        # Factor in daily loss level
        loss_level = self.get_daily_loss_level()
        loss_multiplier_map = {0: 1.0, 1: 1.0, 2: 0.5, 3: 0.25, 4: 0.0}
        loss_multiplier = loss_multiplier_map.get(loss_level, 0.0)

        total_multiplier = vol_multiplier * loss_multiplier
        if total_multiplier <= 0:
            return 0.0

        risk_amount = self.balance * self.cfg.risk_per_trade
        # ATR * 100 converts gold ATR to $ per lot (Institutional standard)
        lot_size = (risk_amount / (current_atr * 100)) * total_multiplier

        # Cap at Max Position Size (e.g., 10% of equity)
        max_notional = self.balance * self.cfg.max_position_size_pct
        price = market_data["close"].iloc[-1]
        max_lots = max_notional / (price * 100)

        final_lots = min(lot_size, max_lots)
        return max(self.cfg.min_lot_size, round(final_lots, 2))

    def _calculate_kelly_sizing(
        self, win_rate: float, avg_win: float, avg_loss: float, pip_value: float
    ) -> float:
        """Fractional Kelly sizing logic from original RiskManager."""
        if avg_loss == 0:
            return self.cfg.min_lot_size

        # Kelly % = W - [(1-W) / R] where R is win/loss ratio
        # Simplified: (W * avg_win - (1-W) * avg_loss) / avg_win
        kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        kelly_fraction = max(0.0, min(kelly_fraction, 0.25))  # Institutional cap

        risk_capital = self.balance * self.cfg.risk_per_trade
        lot_size = (risk_capital * kelly_fraction) / (avg_loss * pip_value)
        return max(self.cfg.min_lot_size, round(lot_size, 2))

    # -- Private filter layers ----------------------------------------------

    def _check_circuit_breaker(self) -> bool:
        """Layer 1: Hard Drawdown Breaker."""
        if self.peak_equity <= 0:
            return True
        drawdown = (self.peak_equity - self.balance) / self.peak_equity
        if drawdown >= self.cfg.max_drawdown:
            logger.critical("CIRCUIT BREAKER: Drawdown %.1f%% hit limit", drawdown * 100)
            if self.monitor:
                self.monitor.alert_circuit_breaker(drawdown)
            return False
        return True

    def _check_consecutive_losses(self) -> bool:
        """Layer 3: Consecutive Loss Limit."""
        return not self.daily.consecutive_losses >= self.cfg.max_losing_streak

    def _check_directional_exposure(
        self, signal: TradeSignal, open_positions: List[Dict[str, Any]]
    ) -> bool:
        """Layer 4: Directional Exposure (30% cap)."""
        net_lots = 0.0
        for pos in open_positions:
            vol = pos.get("volume", 0.0)
            if pos.get("type") == 0:  # BUY
                net_lots += vol
            else:  # SELL
                net_lots -= vol

        # Add potential new position
        net_lots += self.cfg.min_lot_size if signal.direction > 0 else -self.cfg.min_lot_size
        price_estimate = signal.entry_price or 2300.0
        notional = abs(net_lots) * price_estimate * 100
        exposure_pct = notional / self.balance if self.balance > 0 else 1.0

        return exposure_pct <= self.cfg.max_single_direction_pct

    def _check_total_notional(
        self, signal: TradeSignal, open_positions: List[Dict[str, Any]], market_data: pd.DataFrame
    ) -> bool:
        """Layer 4: Total Notional Exposure (100% cap)."""
        total_lots = sum(pos.get("volume", 0.0) for pos in open_positions) + self.cfg.min_lot_size
        price = market_data["close"].iloc[-1] if not market_data.empty else signal.entry_price
        total_notional = total_lots * price * 100
        return total_notional < (self.balance * self.cfg.max_total_notional_pct)

    def _check_symbol_allocation(self, symbol: str) -> bool:
        """Layer 5: Portfolio Allocation."""
        return not (symbol not in ALLOCATION_WEIGHTS and symbol != self.cfg.symbol)

    def _check_minimum_confidence(self, confidence: float) -> bool:
        """Layer 6: Prediction Confidence."""
        return confidence >= self.cfg.min_confidence

    def _check_risk_reward(self, signal: TradeSignal, min_rr: float = 1.5) -> bool:
        """Layer 7: Risk-Reward Ratio."""
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.entry_price)
        if risk == 0:
            return False
        return (reward / risk) >= min_rr

    def _check_model_health(self, health: Optional[dict]) -> bool:
        """Layer 8: Model Health (Drift/Accuracy)."""
        if health is None:
            return True

        if float(health.get("drift", 0.0)) > self.cfg.model_drift_threshold:
            return False
        if float(health.get("accuracy", 1.0)) < self.cfg.model_accuracy_floor:
            return False
        return not float(health.get("calibration", 0.0)) > self.cfg.model_calibration_threshold


__all__ = ["ALLOCATION_WEIGHTS", "DailyStats", "RiskDecision", "RiskManager"]
