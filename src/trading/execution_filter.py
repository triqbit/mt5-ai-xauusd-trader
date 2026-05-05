"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/execution_filter.py
6-layer entry filter cascade to vet signals before execution.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
from scipy import stats

if TYPE_CHECKING:
    from src.core.config import TradingConfig
    from src.core.trade_logger import TradeLogger
    from src.trading.risk_manager import TradeSignal

logger = logging.getLogger(__name__)


@dataclass
class ExecutionDecision:
    """Result of the execution filter cascade."""

    signal: TradeSignal
    is_approved: bool
    confidence_score: float
    blocked_by: str | None = None
    trace: dict[str, Any] = field(default_factory=dict)


class ExecutionFilter:
    """
    Implements a 9-layer validation cascade for trading signals.
    Layers: ATR, Trend Angle, EMA Sequence, Momentum, Session, Drawdown,
    Model Stability, Performance Floor, Confidence Threshold.
    """

    def __init__(
        self,
        max_drawdown: float = 0.15,
        rsi_period: int = 14,
        config: TradingConfig | None = None,
    ):
        self.max_drawdown = max_drawdown
        self.rsi_period = rsi_period
        self.cfg = config

    def validate(
        self,
        signal: TradeSignal,
        market_data: pd.DataFrame,
        current_drawdown: float,
        timestamp: datetime | None = None,
        model_health: dict[str, float] | None = None,
        trade_logger: TradeLogger | None = None,
    ) -> ExecutionDecision:
        """
        Run the full 9-layer filter cascade.
        Evaluates all layers without short-circuiting to capture a full audit trace.
        """
        timestamp = timestamp or signal.timestamp or datetime.now(UTC)
        trace: dict[str, Any] = {}

        # Layer 1: ATR Volatility
        atr_passed, atr_metrics = self._check_atr_volatility_with_metrics(market_data)
        trace["atr_volatility"] = {"passed": atr_passed, **atr_metrics}

        # Layer 2: Trend Angle
        trend_passed, trend_metrics = self._check_trend_angle_with_metrics(
            market_data, signal.direction
        )
        trace["trend_angle"] = {"passed": trend_passed, **trend_metrics}

        # Layer 3: EMA Sequence
        ema_passed, ema_metrics = self._check_ema_sequence_with_metrics(
            market_data, signal.direction
        )
        trace["ema_sequence"] = {"passed": ema_passed, **ema_metrics}

        # Layer 4: Momentum (RSI)
        momentum_passed, momentum_metrics = self._check_momentum_with_metrics(
            market_data, signal.direction
        )
        trace["momentum"] = {"passed": momentum_passed, **momentum_metrics}

        # Layer 5: Session/Time
        session_passed = self._check_session_time(timestamp)
        trace["session_time"] = {"passed": session_passed, "timestamp": timestamp.isoformat()}

        # Layer 6: Drawdown
        drawdown_passed = self._check_drawdown_limit(current_drawdown)
        trace["drawdown_limit"] = {
            "passed": drawdown_passed,
            "current_drawdown": current_drawdown,
            "max_drawdown": self.max_drawdown,
        }

        # Layer 7: Model Stability Guard
        stability_passed, stability_metrics = self._check_model_stability_with_metrics(model_health)
        trace["model_stability"] = {"passed": stability_passed, **stability_metrics}

        # Layer 8: Performance Floor
        perf_passed, perf_metrics = self._check_performance_floor_with_metrics(trade_logger)
        trace["performance_floor"] = {"passed": perf_passed, **perf_metrics}

        # Layer 9: Confidence Threshold
        conf_passed = self._check_dynamic_confidence(signal.confidence)
        trace["confidence_threshold"] = {
            "passed": conf_passed,
            "confidence": signal.confidence,
            "threshold": self.cfg.confidence_threshold if self.cfg else 0.0,
        }

        # Determine final approval
        is_approved = all(t["passed"] for t in trace.values())
        blocked_by = None
        if not is_approved:
            # Identify first failure for backward compatibility in blocked_by field
            failure_order = [
                "atr_volatility",
                "trend_angle",
                "ema_sequence",
                "momentum",
                "session_time",
                "drawdown_limit",
                "model_stability",
                "performance_floor",
                "confidence_threshold",
            ]
            for layer in failure_order:
                if not trace[layer]["passed"]:
                    blocked_by = layer.upper()
                    break

        return ExecutionDecision(
            signal=signal,
            is_approved=is_approved,
            confidence_score=signal.confidence,
            blocked_by=blocked_by,
            trace=trace,
        )

    def _check_atr_volatility(self, df: pd.DataFrame, threshold: float = 3.0) -> bool:
        """Original method - now delegates to metrics version."""
        passed, _ = self._check_atr_volatility_with_metrics(df, threshold)
        return passed

    def _check_atr_volatility_with_metrics(
        self, df: pd.DataFrame, threshold: float = 3.0
    ) -> tuple[bool, dict[str, Any]]:
        """Blocks if current ATR is > threshold * average ATR."""
        if "base_M5_atr" not in df.columns:
            # Fallback calculation if not in DF
            high = df["high"]
            low = df["low"]
            close = df["close"]
            tr = pd.concat(
                [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1
            ).max(axis=1)
            atr = tr.rolling(window=14).mean()
        else:
            atr = df["base_M5_atr"]

        current_atr = float(atr.iloc[-1])
        avg_atr = float(atr.rolling(window=100).mean().iloc[-1])

        if np.isnan(current_atr) or np.isnan(avg_atr):
            return True, {"current_atr": 0.0, "avg_atr": 0.0, "ratio": 0.0}

        ratio = current_atr / avg_atr if avg_atr > 0 else 0.0
        passed = ratio <= threshold
        return passed, {"current_atr": current_atr, "avg_atr": avg_atr, "ratio": ratio}

    def _check_trend_angle(self, df: pd.DataFrame, direction: int, window: int = 20) -> bool:
        """Original method - now delegates to metrics version."""
        passed, _ = self._check_trend_angle_with_metrics(df, direction, window)
        return passed

    def _check_trend_angle_with_metrics(
        self, df: pd.DataFrame, direction: int, window: int = 20
    ) -> tuple[bool, dict[str, Any]]:
        """Validates that the price trend matches signal direction using regression slope of EMA21."""
        ema_col = "base_M5_ema_21"
        if ema_col in df.columns:
            ema_series = df[ema_col]
        elif "close" in df.columns:
            ema_series = df["close"].ewm(span=21, adjust=False).mean()
        else:
            return True, {"slope": 0.0, "reason": "No EMA data"}

        target_ema = ema_series.iloc[-window:]
        if len(target_ema) < window:
            return True, {"slope": 0.0, "reason": "Insufficient data"}

        x = np.arange(len(target_ema))
        slope, _, _, _, _ = stats.linregress(x, target_ema.values)

        if direction > 0:  # BUY
            passed = bool(slope > 0)
        elif direction < 0:  # SELL
            passed = bool(slope < 0)
        else:
            passed = False

        return passed, {"slope": float(slope), "direction": direction}

    def _check_ema_sequence(self, df: pd.DataFrame, direction: int) -> bool:
        """Original method - now delegates to metrics version."""
        passed, _ = self._check_ema_sequence_with_metrics(df, direction)
        return passed

    def _check_ema_sequence_with_metrics(
        self, df: pd.DataFrame, direction: int
    ) -> tuple[bool, dict[str, Any]]:
        """Verifies EMA stack (8 > 21 > 50 > 200 for BUY)."""
        periods = [8, 21, 50, 200]
        emas = {}

        for p in periods:
            col = f"base_M5_ema_{p}"
            if col in df.columns:
                emas[p] = float(df[col].iloc[-1])
            else:
                emas[p] = float(df["close"].ewm(span=p, adjust=False).mean().iloc[-1])

        if direction > 0:  # BUY
            passed = bool(emas[8] > emas[21] > emas[50] > emas[200])
        elif direction < 0:  # SELL
            passed = bool(emas[8] < emas[21] < emas[50] < emas[200])
        else:
            passed = False

        return passed, {"emas": emas, "direction": direction}

    def _check_momentum(self, df: pd.DataFrame, direction: int) -> bool:
        """Original method - now delegates to metrics version."""
        passed, _ = self._check_momentum_with_metrics(df, direction)
        return passed

    def _check_momentum_with_metrics(
        self, df: pd.DataFrame, direction: int
    ) -> tuple[bool, dict[str, Any]]:
        """Validates RSI is in a healthy momentum zone."""
        col = "base_M5_rsi"
        if col in df.columns:
            rsi = float(df[col].iloc[-1])
        else:
            delta = df["close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
            rs = gain / (loss + 1e-8)
            rsi = float(100 - (100 / (1 + rs)).iloc[-1])

        if np.isnan(rsi):
            return True, {"rsi": 0.0}

        if direction > 0:  # BUY
            passed = bool(50 <= rsi <= 75)
        elif direction < 0:  # SELL
            passed = bool(25 <= rsi <= 50)
        else:
            passed = False

        return passed, {"rsi": rsi, "direction": direction}

    def _check_model_stability(self, health: dict[str, float] | None) -> bool:
        """Original method - now delegates to metrics version."""
        passed, _ = self._check_model_stability_with_metrics(health)
        return passed

    def _check_model_stability_with_metrics(
        self, health: dict[str, float] | None
    ) -> tuple[bool, dict[str, Any]]:
        """Blocks if aggregate model drift or accuracy breaches limits."""
        if health is None or self.cfg is None:
            return True, {"drift": 0.0, "accuracy": 1.0}

        drift = float(health.get("drift", 0.0))
        acc = float(health.get("accuracy", 1.0))

        passed = True
        if drift > self.cfg.model_drift_threshold:
            logger.warning(
                "EXECUTION BLOCKED: Model drift %.2f > %.2f", drift, self.cfg.model_drift_threshold
            )
            passed = False

        if acc < self.cfg.model_accuracy_floor:
            logger.warning(
                "EXECUTION BLOCKED: Model accuracy %.2f < %.2f", acc, self.cfg.model_accuracy_floor
            )
            passed = False

        return passed, {
            "drift": drift,
            "accuracy": acc,
            "drift_threshold": self.cfg.model_drift_threshold,
            "accuracy_floor": self.cfg.model_accuracy_floor,
        }

    def _check_performance_floor(self, trade_logger: TradeLogger | None) -> bool:
        """Original method - now delegates to metrics version."""
        passed, _ = self._check_performance_floor_with_metrics(trade_logger)
        return passed

    def _check_performance_floor_with_metrics(
        self, trade_logger: TradeLogger | None
    ) -> tuple[bool, dict[str, Any]]:
        """Blocks if historical win rate drops below floor."""
        if trade_logger is None or self.cfg is None:
            return True, {"win_rate": 1.0, "total_trades": 0}

        report = trade_logger.read_performance_report()
        win_rate = float(report.get("win_rate", 1.0))
        total_trades = int(report.get("total_trades", 0))

        passed = True
        if total_trades >= 20 and win_rate < self.cfg.model_win_rate_floor:
            logger.warning(
                "EXECUTION BLOCKED: Win rate %.2f < %.2f", win_rate, self.cfg.model_win_rate_floor
            )
            passed = False

        return passed, {
            "win_rate": win_rate,
            "total_trades": total_trades,
            "win_rate_floor": self.cfg.model_win_rate_floor,
        }

    def _check_dynamic_confidence(self, confidence: float) -> bool:
        """Enforces configured confidence threshold."""
        if self.cfg is None:
            return True
        return confidence >= self.cfg.confidence_threshold

    def _check_session_time(self, timestamp: datetime) -> bool:
        """Blocks outside institutional trading hours (Sun 17:00 - Fri 16:00 GMT)."""
        weekday = timestamp.weekday()  # Mon=0, Sun=6
        hour = timestamp.hour

        if weekday == 5:  # Saturday
            return False
        if weekday == 6:  # Sunday
            return hour >= 17
        if weekday == 4:  # Friday
            return hour < 16

        return True

    def _check_drawdown_limit(self, current_drawdown: float) -> bool:
        """Blocks if account drawdown exceeds limit."""
        return current_drawdown < self.max_drawdown
