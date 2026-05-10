"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_manager.py
Central risk authority enforcing institutional-grade safety cascades.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from src.core.config import TradingConfig
from src.core.monitor import Monitor
from src.core.schemas import DailyStats, RiskDecision, TradeSignal
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


class RiskManager:
    """
    Central risk authority.
    Every signal must be approved here before reaching the order router.
    Implements the full 8-layer risk filter cascade.
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
        self.open_positions_count: int = 0
        self.trade_logger = logger_db
        self.monitor = monitor
        logger.info("RiskManager initialised | balance=%.2f", account_balance)

    # -- Public API ---------------------------------------------------------

    def approve(
        self,
        signal: TradeSignal,
        market_data: pd.DataFrame,
        open_positions: List[Dict[str, Any]],
        signal_id: Optional[int] = None,
        model_health: Optional[dict] = None,
    ) -> RiskDecision:
        """
        Run the full 8-layer risk filter cascade.
        Returns RiskDecision only if ALL layers pass.

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
        trace = {}

        # Layer 1: Circuit Breakers (Equity Drawdown)
        drawdown_passed = self._check_drawdown_breaker()
        trace["circuit_breaker"] = drawdown_passed
        if not drawdown_passed:
            return self._reject("Hard drawdown limit reached", signal, trace, signal_id)

        # Layer 2: Daily Loss Limits (Level 4)
        loss_level = self.get_daily_loss_level()
        daily_loss_passed = loss_level < 4
        trace["daily_loss"] = daily_loss_passed
        if not daily_loss_passed:
            return self._reject("Daily loss limit reached (Level 4)", signal, trace, signal_id)

        # Layer 3: Activity Limits
        max_trades_passed = self.daily.trade_count < self.cfg.max_trades_per_day
        max_streak_passed = self.daily.consecutive_losses < self.cfg.max_losing_streak
        trace["max_trades"] = max_trades_passed
        trace["max_streak"] = max_streak_passed
        if not max_trades_passed:
            return self._reject("Max daily trades reached", signal, trace, signal_id)
        if not max_streak_passed:
            return self._reject("Max consecutive losses reached", signal, trace, signal_id)

        # Layer 4: Exposure Limits
        max_pos_passed = len(open_positions) < self.cfg.max_positions
        dir_exp_passed = self._check_directional_exposure(signal, open_positions)
        notional_passed = self._check_total_notional(signal, open_positions, market_data)
        trace["max_positions"] = max_pos_passed
        trace["directional_exposure"] = dir_exp_passed
        trace["total_notional"] = notional_passed

        if not max_pos_passed:
            return self._reject("Max concurrent positions reached", signal, trace, signal_id)
        if not dir_exp_passed:
            return self._reject("Max directional exposure reached (30%)", signal, trace, signal_id)
        if not notional_passed:
            return self._reject("Total notional exposure exceeds equity", signal, trace, signal_id)

        # Layer 5: Symbol Allocation
        symbol_passed = signal.symbol in ALLOCATION_WEIGHTS
        trace["symbol_allocation"] = symbol_passed
        if not symbol_passed:
            return self._reject(f"Symbol {signal.symbol} not in approved list", signal, trace, signal_id)

        # Layer 6: Prediction Limits
        confidence_passed = signal.confidence >= self.cfg.min_confidence
        trace["min_confidence"] = confidence_passed
        if not confidence_passed:
            return self._reject(
                f"Confidence {signal.confidence:.2f} below {self.cfg.min_confidence}",
                signal,
                trace,
                signal_id,
            )

        # Layer 7: Risk-Reward Validation
        rr_passed = self._check_risk_reward(signal)
        trace["risk_reward"] = rr_passed
        if not rr_passed:
            return self._reject("Risk-Reward ratio below 1.5", signal, trace, signal_id)

        # Layer 8: Model Health
        health_passed = self._check_model_health(model_health)
        trace["model_health"] = health_passed
        if not health_passed:
            return self._reject("Model health metrics below threshold", signal, trace, signal_id)

        # Calculate final lot size using ATR-based sizing
        adjusted_lots = self.calculate_position_size(signal.symbol, market_data)

        if adjusted_lots < self.cfg.min_lot_size:
            return self._reject(
                f"Calculated lot size {adjusted_lots} below minimum", signal, trace, signal_id
            )

        return RiskDecision(
            is_approved=True,
            reason="Approved",
            adjusted_lot_size=adjusted_lots,
            trace=trace
        )

    def calculate_position_size(self, symbol: str, market_data: pd.DataFrame) -> float:
        """
        ATR-based position sizing.
        """
        if market_data.empty or "atr" not in market_data.columns:
            return self.cfg.min_lot_size

        current_atr = market_data["atr"].iloc[-1]
        # Approx 30 days of M5 (8640 candles)
        avg_atr = market_data["atr"].tail(8640).mean()

        vol_multiplier = 1.0
        ratio = current_atr / avg_atr if avg_atr > 0 else 1.0

        if ratio > self.cfg.volatility_extreme_threshold:
            return 0.0
        elif ratio > self.cfg.volatility_very_high_threshold:
            vol_multiplier = 0.5
        elif ratio > self.cfg.volatility_high_threshold:
            vol_multiplier = 0.75

        loss_multiplier = self._get_size_multiplier_from_loss()
        total_multiplier = vol_multiplier * loss_multiplier

        if total_multiplier <= 0:
            return 0.0

        # Sizing: risk 1% (cfg.risk_per_trade) of balance
        risk_amount = self.balance * self.cfg.risk_per_trade
        # ATR * 100 converts gold ATR to $ per lot (Standard Gold Lot size 100oz)
        lot_size = (risk_amount / (current_atr * 100)) * total_multiplier

        # Cap at Max Position Size (e.g. 10% of equity)
        max_notional = self.balance * self.cfg.max_position_size_pct
        price = market_data["close"].iloc[-1]
        max_lots = max_notional / (price * 100)

        final_lots = min(lot_size, max_lots)
        final_lots = max(self.cfg.min_lot_size, round(final_lots, 2))

        return final_lots

    def update_equity(self, current_equity: float, realized_pnl: float = 0) -> None:
        """Update equity trackers and daily stats."""
        self.balance = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        if realized_pnl != 0:
            self.daily.realised_pnl += realized_pnl
            self.daily.trade_count += 1
            if realized_pnl < 0:
                self.daily.consecutive_losses += 1
            else:
                self.daily.consecutive_losses = 0

        if current_equity > self.daily.peak_equity:
            self.daily.peak_equity = current_equity

    def record_pnl(self, pnl: float) -> None:
        """Legacy compatibility for record_pnl."""
        self.update_equity(self.balance + pnl, realized_pnl=pnl)

    def reset_daily(self) -> None:
        """Must be called at the start of each trading day."""
        if self.monitor:
            self.monitor.send_daily_summary(self.daily.realised_pnl, self.daily.trade_count)
        self.daily = DailyStats(peak_equity=self.balance)
        logger.info("Daily stats reset")

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

    # -- Internal cascade layers -------------------------------------------

    def _reject(
        self, reason: str, signal: TradeSignal, trace: Dict[str, bool], signal_id: Optional[int] = None
    ) -> RiskDecision:
        logger.warning(
            "Signal REJECTED | %s %s | Reason: %s",
            signal.symbol,
            signal.direction,
            reason,
        )
        if self.trade_logger:
            self.trade_logger.log_risk_event(
                event_type="SIGNAL_REJECTED",
                description=reason,
                symbol=signal.symbol,
                signal_id=signal_id,
            )
        return RiskDecision(is_approved=False, reason=reason, adjusted_lot_size=0.0, trace=trace)

    def _check_drawdown_breaker(self) -> bool:
        """Layer 1: Equity Drawdown."""
        if self.peak_equity <= 0:
            return True
        drawdown = (self.peak_equity - self.balance) / self.peak_equity
        if drawdown >= self.cfg.max_drawdown:
            logger.critical("CIRCUIT BREAKER: Drawdown %.2f%% hit limit", drawdown * 100)
            if self.monitor:
                self.monitor.alert_circuit_breaker(drawdown)
            return False
        return True

    def _check_directional_exposure(
        self, signal: TradeSignal, open_positions: List[Dict[str, Any]]
    ) -> bool:
        """Layer 4: 30% net directional exposure."""
        net_lots = 0.0
        for pos in open_positions:
            vol = pos.get("volume", 0.0)
            if pos.get("type") == 0:  # BUY (MT5 constant)
                net_lots += vol
            else:  # SELL (MT5 constant)
                net_lots -= vol

        net_lots += signal.lot_size if signal.direction > 0 else -signal.lot_size
        price_estimate = 2300.0  # Gold estimate
        notional = abs(net_lots) * price_estimate * 100
        exposure_pct = notional / self.balance if self.balance > 0 else 1.0

        return exposure_pct <= self.cfg.max_single_direction_pct

    def _check_total_notional(
        self, signal: TradeSignal, open_positions: List[Dict[str, Any]], market_data: pd.DataFrame
    ) -> bool:
        """Layer 4: Total notional < 1000% equity (10x leverage)."""
        total_lots = sum(pos.get("volume", 0.0) for pos in open_positions) + signal.lot_size
        price = market_data["close"].iloc[-1] if not market_data.empty else 2300.0
        total_notional = total_lots * price * 100
        return total_notional < (self.balance * self.cfg.max_total_notional_pct)

    def _check_risk_reward(self, signal: TradeSignal, min_rr: float = 1.5) -> bool:
        """Layer 7: Minimum 1.5 Risk-Reward."""
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.entry_price)
        return reward >= (risk * min_rr) if risk > 0 else False

    def _check_model_health(self, health: Optional[Dict[str, float]]) -> bool:
        """Layer 8: Model Health Metrics."""
        if health is None:
            return True

        drift = health.get("drift", 0.0)
        accuracy = health.get("accuracy", 1.0)
        calibration = health.get("calibration", 0.0)

        if drift > self.cfg.model_drift_threshold:
            return False
        if accuracy < self.cfg.model_accuracy_floor:
            return False
        return calibration <= self.cfg.model_calibration_threshold

    def _get_size_multiplier_from_loss(self) -> float:
        """Multiplier based on daily loss level."""
        level = self.get_daily_loss_level()
        mapping = {0: 1.0, 1: 1.0, 2: 0.5, 3: 0.25, 4: 0.0}
        return mapping.get(level, 0.0)


__all__ = ["ALLOCATION_WEIGHTS", "RiskManager"]
