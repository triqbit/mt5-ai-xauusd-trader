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
from typing import Dict, Optional

import pandas as pd

from src.core.config import TradingConfig
from src.core.monitor import Monitor
from src.core.schemas import TradeSignal
from src.core.trade_logger import TradeLogger
from src.models.regime_detector import MarketRegime, RegimeInfo

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
        regime_info: Optional[RegimeInfo] = None,
    ) -> bool:
        """
        Run the full risk filter cascade.
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
        elif not self._check_consecutive_losses():
            rejection_reason = "Max consecutive losses reached"
        elif not self._check_model_health(model_health):
            rejection_reason = "Model health metrics below threshold"
        elif not self._check_volatility_breaker(market_data):
            rejection_reason = "Extreme volatility breaker triggered"
        elif not self._check_regime_safety(signal.confidence, regime_info):
            rejection_reason = "Regime-based safety check failed"

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
        confidence: float = 1.0,
        market_data: Optional[pd.DataFrame] = None,
    ) -> float:
        """
        Position sizing combining Kelly Criterion with confidence and volatility scaling.
        Returns lot size capped at max risk per trade.
        """
        if avg_loss == 0:
            return self.cfg.min_lot_size

        # 1. Base Kelly sizing
        kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        kelly_fraction = max(0.0, min(kelly_fraction, 0.25))  # cap at 25% Kelly

        # 2. Confidence scaling (per RISK_LIMITS.md)
        conf_multiplier = 1.0
        if confidence < self.cfg.min_confidence:
            conf_multiplier = 0.0
        elif confidence < 0.65:
            conf_multiplier = 0.5
        # High/Very High confidence (>= 0.65) use 1.0x

        # 3. Volatility scaling (per RISK_LIMITS.md)
        vol_multiplier = 1.0
        if market_data is not None and not market_data.empty:
            atr_col = "base_M5_atr" if "base_M5_atr" in market_data.columns else "atr"
            if atr_col in market_data.columns:
                current_atr = market_data[atr_col].iloc[-1]
                # Approx 30 days of M5 data (8640 bars) if available, otherwise use what we have
                window = min(len(market_data), 8640)
                avg_atr = market_data[atr_col].tail(window).mean()
                ratio = current_atr / avg_atr if avg_atr > 0 else 1.0

                if ratio > self.cfg.volatility_extreme_threshold:
                    vol_multiplier = 0.0
                elif ratio > self.cfg.volatility_very_high_threshold:
                    vol_multiplier = 0.5
                elif ratio > self.cfg.volatility_high_threshold:
                    vol_multiplier = 0.75

        total_multiplier = conf_multiplier * vol_multiplier
        risk_capital = self.balance * self.cfg.risk_per_trade * total_multiplier

        if risk_capital <= 0:
            return 0.0

        lot_size = (risk_capital * kelly_fraction) / (avg_loss * pip_value)

        # Cap at Max Position Size (10% of equity)
        max_notional = self.balance * self.cfg.max_position_size_pct
        # Fallback price if market_data not available
        price = market_data["close"].iloc[-1] if market_data is not None and not market_data.empty else 2300.0
        # XAUUSD 1 lot = 100 oz. Notional = price * lot * 100
        max_lots = max_notional / (price * 100)

        lot_size = min(lot_size, max_lots)
        lot_size = max(self.cfg.min_lot_size, round(lot_size, 2))

        logger.info(
            "Sizing | symbol=%s | kelly=%.3f | conf_mult=%.2f | vol_mult=%.2f | lots=%.2f",
            symbol,
            kelly_fraction,
            conf_multiplier,
            vol_multiplier,
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

    def _check_minimum_confidence(self, confidence: float, threshold: Optional[float] = None) -> bool:
        target_threshold = threshold if threshold is not None else self.cfg.min_confidence
        if confidence < target_threshold:
            logger.warning(
                "Confidence %.2f below threshold %.2f", confidence, target_threshold
            )
            return False
        return True

    def _check_volatility_breaker(self, market_data: Optional[pd.DataFrame]) -> bool:
        """Halt trading if volatility is extreme (>3x normal)."""
        if market_data is None or market_data.empty:
            return True

        atr_col = "base_M5_atr" if "base_M5_atr" in market_data.columns else "atr"
        if atr_col not in market_data.columns:
            return True

        current_atr = market_data[atr_col].iloc[-1]
        window = min(len(market_data), 8640)
        avg_atr = market_data[atr_col].tail(window).mean()
        ratio = current_atr / avg_atr if avg_atr > 0 else 1.0

        if ratio > self.cfg.volatility_extreme_threshold:
            logger.critical(
                "VOLATILITY BREAKER: ratio=%.2f hit extreme threshold %.2f",
                ratio,
                self.cfg.volatility_extreme_threshold,
            )
            return False
        return True

    def _check_regime_safety(self, confidence: float, regime_info: Optional[RegimeInfo]) -> bool:
        """Enforce stricter confidence floors in unstable market regimes."""
        if regime_info is None:
            return True

        label = regime_info.label
        # Institutional standards for XAUUSD stability
        regime_thresholds = {
            MarketRegime.NEWS_SHOCK: 0.80,         # Extremely high bar during shocks
            MarketRegime.VOLATILE_BREAKOUT: 0.70, # Higher bar for breakouts
            MarketRegime.MEAN_REVERSION: 0.65,    # Stricter for counter-trend
            MarketRegime.TRENDING: 0.55,          # Standard
            MarketRegime.RANGING: 0.55,           # Standard
            MarketRegime.LOW_VOLATILITY_DRIFT: 0.60, # Slightly higher for low-vol drift
        }

        required_conf = regime_thresholds.get(label, self.cfg.min_confidence)

        if confidence < required_conf:
            logger.warning(
                "Regime Safety Block | regime=%s | confidence=%.2f < required=%.2f",
                label.value,
                confidence,
                required_conf,
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


__all__ = ["ALLOCATION_WEIGHTS", "DailyStats", "RiskManager"]
