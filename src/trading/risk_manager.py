"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_manager.py

Enterprise risk management engine implementing:
  - ATR-based position sizing (Institutional)
  - 4-Level Cascading Daily Loss limits
  - 30% Directional exposure caps
  - 10x Notional leverage limits
  - 8-layer entry filter cascade

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


@dataclass
class RiskDecision:
    """Decision details from the RiskEngine/Manager."""

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
    Consolidated institutional risk engine enforcing RISK_LIMITS.md.
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

    def approve(
        self,
        signal: TradeSignal,
        signal_id: Optional[int] = None,
        model_health: Optional[dict] = None,
        market_data: Optional[pd.DataFrame] = None,
        open_positions_raw: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """
        Public gate for trade signals.
        Delegates to validate_signal for institutional compatibility.
        """
        decision = self.validate_signal(
            signal, market_data, open_positions_raw, model_health
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

    def validate_signal(
        self,
        signal: TradeSignal,
        market_data: Optional[pd.DataFrame] = None,
        open_positions: Optional[List[Dict[str, Any]]] = None,
        model_health: Optional[dict] = None,
    ) -> RiskDecision:
        """
        Institutional 8-layer validation cascade.
        """
        # Layer 1: Circuit Breaker
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
        # Use open_positions if provided, otherwise fallback to internal tracker
        active_pos_count = len(open_positions) if open_positions is not None else len(self.open_positions)
        if active_pos_count >= self.cfg.max_positions:
            return RiskDecision(False, "Max concurrent positions reached")

        if open_positions is not None and not self._check_directional_exposure(signal, open_positions):
            return RiskDecision(False, "Max directional exposure reached (30%)")

        if open_positions is not None and market_data is not None and not self._check_total_notional(signal, open_positions, market_data):
            return RiskDecision(False, "Total notional exposure exceeds limit")

        # Layer 5: Symbol Allocation
        if signal.symbol != self.cfg.symbol:
            return RiskDecision(False, f"Symbol {signal.symbol} not in approved list")

        # Layer 6: Prediction Limits
        if signal.confidence < self.cfg.min_confidence:
            return RiskDecision(False, f"Confidence {signal.confidence:.2f} below {self.cfg.min_confidence}")

        # Layer 7: Risk-Reward Validation
        if not self._check_risk_reward(signal):
            return RiskDecision(False, "Risk-Reward ratio below 1.5")

        # Layer 8: Model Health
        if not self._check_model_health(model_health):
            return RiskDecision(False, "Model health metrics below threshold")

        # Calculate lot size
        lot_size = 0.0
        if market_data is not None:
            lot_size = self.size_position(signal.symbol, market_data)

        return RiskDecision(True, "Approved", lot_size)

    def size_position(
        self,
        symbol: str,
        market_data: pd.DataFrame,
    ) -> float:
        """
        Institutional ATR-based position sizing.
        """
        if market_data.empty or "atr" not in market_data.columns:
            return self.cfg.min_lot_size

        current_atr = market_data["atr"].iloc[-1]
        avg_atr = market_data["atr"].tail(8640).mean()  # Approx 30 days of M5

        vol_multiplier = 1.0
        ratio = float(current_atr / avg_atr) if avg_atr > 0 else 1.0

        if ratio > getattr(self.cfg, "volatility_extreme_threshold", 3.0):
            return 0.0
        elif ratio > getattr(self.cfg, "volatility_very_high_threshold", 2.0):
            vol_multiplier = 0.5
        elif ratio > getattr(self.cfg, "volatility_high_threshold", 1.5):
            vol_multiplier = 0.75

        loss_multiplier = self.get_size_multiplier_from_loss()
        total_multiplier = vol_multiplier * loss_multiplier

        if total_multiplier <= 0:
            return 0.0

        # Sizing: risk 1% of balance
        risk_amount = self.balance * self.cfg.risk_per_trade
        # ATR * 100 converts gold ATR to $ per lot
        lot_size = (risk_amount / (current_atr * 100)) * total_multiplier

        # Cap at Max Position Size (e.g. 10% of equity)
        max_notional_pct = getattr(self.cfg, "max_position_size_pct", 0.1)
        max_notional = self.balance * max_notional_pct
        price = market_data["close"].iloc[-1]
        max_lots = max_notional / (price * 100)

        final_lots = min(lot_size, max_lots)
        final_lots = max(self.cfg.min_lot_size, round(final_lots, 2))

        logger.debug(
            "ATR sizing | ratio=%.2f vol_mult=%.2f loss_mult=%.2f lots=%.2f",
            ratio,
            vol_multiplier,
            loss_multiplier,
            final_lots,
        )
        return final_lots

    def update_equity(self, current_equity: float) -> None:
        self.balance = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        if current_equity > self.daily.peak_equity:
            self.daily.peak_equity = current_equity

    def record_pnl(self, pnl: float) -> None:
        self.daily.realised_pnl += pnl
        self.daily.trade_count += 1
        if pnl < 0:
            self.daily.consecutive_losses += 1
        else:
            self.daily.consecutive_losses = 0

    def reset_daily(self) -> None:
        if self.monitor:
            self.monitor.send_daily_summary(self.daily.realised_pnl, self.daily.trade_count)
        self.daily = DailyStats(peak_equity=self.balance)
        logger.info("Daily stats reset")

    def get_daily_loss_level(self) -> int:
        if self.daily.peak_equity <= 0 or self.daily.realised_pnl >= 0:
            return 0
        loss_pct = abs(self.daily.realised_pnl) / self.daily.peak_equity
        if loss_pct >= self.cfg.max_daily_loss:
            return 4
        if loss_pct >= getattr(self.cfg, "daily_loss_lvl3", 0.05):
            return 3
        if loss_pct >= getattr(self.cfg, "daily_loss_lvl2", 0.03):
            return 2
        if loss_pct >= getattr(self.cfg, "daily_loss_lvl1", 0.01):
            return 1
        return 0

    def get_size_multiplier_from_loss(self) -> float:
        level = self.get_daily_loss_level()
        mapping = {0: 1.0, 1: 1.0, 2: 0.5, 3: 0.25, 4: 0.0}
        return mapping.get(level, 0.0)

    # -- Private filter layers ----------------------------------------------
    def _check_consecutive_losses(self) -> bool:
        return self.daily.consecutive_losses < self.cfg.max_losing_streak

    def _check_model_health(self, health: Optional[dict]) -> bool:
        if health is None:
            return True
        drift = float(health.get("drift", 0.0))
        accuracy = float(health.get("accuracy", 1.0))
        calibration = float(health.get("calibration", 0.0))
        if drift > self.cfg.model_drift_threshold:
            return False
        if accuracy < self.cfg.model_accuracy_floor:
            return False
        return calibration <= self.cfg.model_calibration_threshold

    def _check_circuit_breaker(self) -> bool:
        if self.peak_equity <= 0:
            return True
        drawdown = (self.peak_equity - self.balance) / self.peak_equity
        if drawdown >= self.cfg.max_drawdown:
            if self.monitor:
                self.monitor.alert_circuit_breaker(drawdown)
            return False
        return True

    def _check_directional_exposure(
        self, signal: TradeSignal, open_positions: List[Dict[str, Any]]
    ) -> bool:
        net_lots = 0.0
        for pos in open_positions:
            vol = pos.get("volume", 0.0)
            if pos.get("type") == 0:  # BUY
                net_lots += vol
            else:  # SELL
                net_lots -= vol
        net_lots += self.cfg.min_lot_size if signal.direction > 0 else -self.cfg.min_lot_size
        price_estimate = 2350.0  # Gold estimate
        notional = abs(net_lots) * price_estimate * 100
        exposure_pct = notional / self.balance if self.balance > 0 else 1.0
        return exposure_pct <= getattr(self.cfg, "max_single_direction_pct", 0.3)

    def _check_total_notional(
        self, signal: TradeSignal, open_positions: List[Dict[str, Any]], market_data: pd.DataFrame
    ) -> bool:
        total_lots = sum(pos.get("volume", 0.0) for pos in open_positions) + self.cfg.min_lot_size
        price = market_data["close"].iloc[-1] if not market_data.empty else 2350.0
        total_notional = total_lots * price * 100
        max_total_pct = getattr(self.cfg, "max_total_notional_pct", 10.0)
        return total_notional < (self.balance * max_total_pct)

    def _check_risk_reward(self, signal: TradeSignal, min_rr: float = 1.5) -> bool:
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.entry_price)
        return reward >= (risk * min_rr) if risk > 0 else False


__all__ = ["DailyStats", "RiskDecision", "RiskManager"]
