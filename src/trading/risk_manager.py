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
    Enforces RISK_LIMITS.md safeguards via an 8-layer cascade.
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
        market_data: Optional[pd.DataFrame] = None,
        open_positions: Optional[List[Dict[str, Any]]] = None,
        model_health: Optional[Dict[str, float]] = None,
        signal_id: Optional[int] = None,
    ) -> RiskDecision:
        """
        Run the full 8-layer risk filter cascade.
        Returns RiskDecision indicating approval status, reason, and adjusted lot size.

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
        trace: Dict[str, Any] = {}
        open_positions = open_positions or []

        # Layer 1: Circuit Breakers (Equity Drawdown)
        drawdown_passed = self._check_circuit_breaker()
        trace["circuit_breaker"] = {"passed": drawdown_passed}
        if not drawdown_passed:
            return RiskDecision(is_approved=False, reason="Hard drawdown limit reached", trace=trace)

        # Layer 2: Daily Loss Limits
        daily_loss_lvl = self.get_daily_loss_level()
        trace["daily_loss"] = {"passed": daily_loss_lvl < 4, "level": daily_loss_lvl}
        if daily_loss_lvl >= 4:
            return RiskDecision(is_approved=False, reason="Daily loss limit reached (Level 4)", trace=trace)

        # Layer 3: Activity Limits
        trade_count_passed = self.daily.trade_count < self.cfg.max_trades_per_day
        consecutive_losses_passed = self._check_consecutive_losses()
        trace["activity_limits"] = {
            "trade_count_passed": trade_count_passed,
            "consecutive_losses_passed": consecutive_losses_passed,
            "trade_count": self.daily.trade_count,
            "consecutive_losses": self.daily.consecutive_losses
        }
        if not trade_count_passed:
            return RiskDecision(is_approved=False, reason="Max daily trades reached", trace=trace)
        if not consecutive_losses_passed:
            return RiskDecision(is_approved=False, reason="Max consecutive losses reached", trace=trace)

        # Layer 4: Exposure Limits
        max_pos_passed = len(open_positions) < self.cfg.max_positions
        dir_exposure_passed = self._check_directional_exposure(signal, open_positions)
        notional_passed = self._check_total_notional(signal, open_positions, market_data)

        trace["exposure_limits"] = {
            "max_positions_passed": max_pos_passed,
            "directional_exposure_passed": dir_exposure_passed,
            "total_notional_passed": notional_passed,
            "open_positions_count": len(open_positions)
        }

        if not max_pos_passed:
            return RiskDecision(is_approved=False, reason="Max concurrent positions reached", trace=trace)
        if not dir_exposure_passed:
            return RiskDecision(is_approved=False, reason="Max directional exposure reached (30%)", trace=trace)
        if not notional_passed:
            return RiskDecision(is_approved=False, reason="Total notional exposure exceeds equity", trace=trace)

        # Layer 5: Symbol Allocation
        symbol_passed = self._check_symbol_allocation(signal.symbol)
        trace["symbol_allocation"] = {"passed": symbol_passed}
        if not symbol_passed:
            return RiskDecision(is_approved=False, reason=f"Symbol {signal.symbol} not in approved list", trace=trace)

        # Layer 6: Prediction Limits
        confidence_passed = signal.confidence >= self.cfg.min_confidence
        trace["prediction_limits"] = {"passed": confidence_passed, "confidence": signal.confidence, "min_required": self.cfg.min_confidence}
        if not confidence_passed:
            return RiskDecision(is_approved=False, reason=f"Confidence {signal.confidence:.2f} below {self.cfg.min_confidence}", trace=trace)

        # Layer 7: Risk-Reward Validation
        rr_passed = self._check_risk_reward(signal)
        trace["risk_reward"] = {"passed": rr_passed}
        if not rr_passed:
            return RiskDecision(is_approved=False, reason="Risk-Reward ratio below 1.5", trace=trace)

        # Layer 8: Model Health
        health_passed = self._check_model_health(model_health)
        trace["model_health"] = {"passed": health_passed, "metrics": model_health}
        if not health_passed:
            return RiskDecision(is_approved=False, reason="Model health metrics below threshold", trace=trace)

        # Calculate adjusted lot size
        adjusted_lots = self.calculate_position_size(signal.symbol, market_data)
        trace["position_sizing"] = {"adjusted_lots": adjusted_lots}

        if adjusted_lots < self.cfg.min_lot_size:
            return RiskDecision(is_approved=False, reason=f"Calculated lot size {adjusted_lots} below minimum", trace=trace)

        return RiskDecision(is_approved=True, reason="Approved", adjusted_lot_size=adjusted_lots, trace=trace)

    def calculate_position_size(self, symbol: str, market_data: Optional[pd.DataFrame]) -> float:
        """
        ATR-based position sizing according to RISK_LIMITS.md.
        """
        if market_data is None or market_data.empty:
            return self.cfg.min_lot_size

        # Support both 'atr' and 'base_M5_atr' column names
        atr_col = "base_M5_atr" if "base_M5_atr" in market_data.columns else "atr"
        if atr_col not in market_data.columns:
            return self.cfg.min_lot_size

        current_atr = market_data[atr_col].iloc[-1]
        avg_atr = market_data[atr_col].tail(8640).mean()  # Approx 30 days of M5

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

        # Sizing: risk 1% (cfg.risk_per_trade) of balance
        risk_amount = self.balance * self.cfg.risk_per_trade
        # ATR * 100 converts gold ATR to $ per lot (approximate for XAUUSD)
        # For other symbols, this might need adjustment, but focus is XAUUSD.
        multiplier = 100.0 if "XAU" in symbol else 1.0

        # Avoid division by zero
        if current_atr <= 0 or multiplier <= 0:
            return self.cfg.min_lot_size

        lot_size = (risk_amount / (current_atr * multiplier)) * total_multiplier

        # Cap at Max Position Size (10% of equity)
        max_notional = self.balance * self.cfg.max_position_size_pct
        price = market_data["close"].iloc[-1]
        max_lots = max_notional / (price * multiplier) if price > 0 and multiplier > 0 else 0.0

        final_lots = lot_size
        if max_lots > 0:
             final_lots = min(lot_size, max_lots)
        final_lots = max(self.cfg.min_lot_size, round(final_lots, 2))

        return final_lots

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
        """
        Layer 1: Equity Drawdown.
        """
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

        # Factor in the new signal
        net_lots += self.cfg.min_lot_size if signal.direction > 0 else -self.cfg.min_lot_size

        # Estimate notional value (Simplified for XAUUSD focus)
        price_estimate = 2300.0
        multiplier = 100.0 if "XAU" in signal.symbol else 1.0
        notional = abs(net_lots) * price_estimate * multiplier
        exposure_pct = notional / self.balance if self.balance > 0 else 1.0

        return exposure_pct <= self.cfg.max_single_direction_pct

    def _check_total_notional(
        self, signal: TradeSignal, open_positions: List[Dict[str, Any]], market_data: Optional[pd.DataFrame]
    ) -> bool:
        """Layer 4: Total notional < 100% equity."""
        total_lots = sum(pos.get("volume", 0.0) for pos in open_positions) + self.cfg.min_lot_size
        price = market_data["close"].iloc[-1] if market_data is not None and not market_data.empty else 2300.0
        multiplier = 100.0 if "XAU" in signal.symbol else 1.0
        total_notional = total_lots * price * multiplier
        return total_notional < (self.balance * self.cfg.max_total_notional_pct)

    def get_size_multiplier_from_loss(self) -> float:
        """Multiplier based on daily loss level."""
        level = self.get_daily_loss_level()
        mapping = {0: 1.0, 1: 1.0, 2: 0.5, 3: 0.25, 4: 0.0}
        return mapping.get(level, 0.0)

    def _check_symbol_allocation(self, symbol: str) -> bool:
        """Block trading on symbols not in the All-Weather portfolio."""
        if symbol not in ALLOCATION_WEIGHTS:
            logger.warning("Symbol %s not in approved portfolio", symbol)
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
