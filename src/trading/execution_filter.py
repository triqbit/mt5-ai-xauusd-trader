"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/execution_filter.py
10-layer entry filter cascade to vet signals before execution.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from collections import deque
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
from scipy import stats

from src.core.schemas import ExecutionDecision

if TYPE_CHECKING:
    from src.core.config import TradingConfig
    from src.core.schemas import TradeSignal

logger = logging.getLogger(__name__)


class ExecutionFilter:
    """
    Implements a 10-layer validation cascade for trading signals.
    Layers:
        1. ATR Volatility Threshold
        2. Trend Angle Confirmation
        3. EMA Sequence Check
        4. Momentum Filter
        5. Session/Time Filter
        6. Drawdown Circuit Breaker
        7. Model Stability (Drift/Accuracy)
        8. Performance Floor (Win Rate)
        9. Confidence Threshold
        10. Signal Consistency (Flicker Guard)
    """

    def __init__(
        self,
        max_drawdown: float = 0.12,
        rsi_period: int = 14,
        config: TradingConfig | None = None,
    ):
        self.max_drawdown = max_drawdown
        self.rsi_period = rsi_period
        self.cfg = config
        self._signal_history: dict[str, deque[int]] = {}

    def validate(
        self,
        signal: TradeSignal,
        market_data: pd.DataFrame,
        current_drawdown: float,
        timestamp: datetime | None = None,
        precomputed_metrics: dict[str, Any] | None = None,
        model_health: dict[str, Any] | None = None,
        trade_logger: Any | None = None,
        **kwargs: Any,
    ) -> ExecutionDecision:
        """
        Run the full 10-layer filter cascade.
        Evaluates all layers without short-circuiting to capture a full audit trace.

        Args:
            signal: The signal to validate.
            market_data: DataFrame with OHLCV and technical indicators.
            current_drawdown: Current account drawdown (0.0 to 1.0).
            timestamp: Evaluation time.
            precomputed_metrics: Optional dictionary containing pre-calculated metrics.
            model_health: Optional model health metrics.
            trade_logger: Optional trade logger for win rate check.
        """
        if timestamp is None:
            timestamp = signal.timestamp or datetime.now(UTC)

        trace: dict[str, Any] = {}
        metrics = precomputed_metrics or {}

        # Layer 1: ATR Volatility
        atr_passed, atr_metrics = self._check_atr_volatility_with_metrics(
            market_data, precomputed=metrics.get("atr_volatility")
        )
        trace["atr_volatility"] = {
            "passed": bool(atr_passed),
            **atr_metrics,
        }

        # Layer 2: Trend Angle
        trend_passed, trend_metrics = self._check_trend_angle_with_metrics(
            market_data,
            signal.direction,
            precomputed=metrics.get("trend_angle"),
        )
        trace["trend_angle"] = {
            "passed": bool(trend_passed),
            **trend_metrics,
        }

        # Layer 3: EMA Sequence
        ema_passed, ema_metrics = self._check_ema_sequence_with_metrics(
            market_data,
            signal.direction,
            precomputed=metrics.get("ema_sequence"),
        )
        trace["ema_sequence"] = {
            "passed": bool(ema_passed),
            **ema_metrics,
        }

        # Layer 4: Momentum (RSI)
        momentum_passed, momentum_metrics = self._check_momentum_with_metrics(
            market_data,
            signal.direction,
            precomputed=metrics.get("momentum"),
        )
        trace["momentum"] = {
            "passed": bool(momentum_passed),
            **momentum_metrics,
        }

        # Layer 5: Session/Time
        session_passed = self._check_session_time(timestamp)
        trace["session_time"] = {
            "passed": bool(session_passed),
            "timestamp": timestamp.isoformat(),
        }

        # Layer 6: Drawdown
        drawdown_passed = self._check_drawdown_limit(current_drawdown)
        trace["drawdown_limit"] = {
            "passed": bool(drawdown_passed),
            "current_drawdown": current_drawdown,
            "max_drawdown": self.max_drawdown,
        }

        # Layer 7: Model Stability
        stability_passed = True
        stability_trace: dict[str, Any] = {"passed": True}
        if model_health:
            drift = model_health.get("drift", 0.0)
            accuracy = model_health.get("accuracy", 1.0)
            drift_threshold = self.cfg.model_drift_threshold if self.cfg else 0.3
            accuracy_floor = self.cfg.model_accuracy_floor if self.cfg else 0.5
            stability_passed = (drift < drift_threshold) and (accuracy >= accuracy_floor)
            stability_trace = {
                "passed": bool(stability_passed),
                "drift": drift,
                "accuracy": accuracy,
                "drift_threshold": drift_threshold,
                "accuracy_floor": accuracy_floor
            }
        trace["model_stability"] = stability_trace

        # Layer 8: Performance Floor
        perf_passed = True
        perf_trace: dict[str, Any] = {"passed": True}
        if trade_logger:
            perf = trade_logger.read_performance_report()
            win_rate = perf.get("win_rate", 1.0)
            win_rate_floor = self.cfg.model_win_rate_floor if self.cfg else 0.45
            perf_passed = win_rate >= win_rate_floor
            perf_trace = {
                "passed": bool(perf_passed),
                "win_rate": win_rate,
                "win_rate_floor": win_rate_floor
            }
        trace["performance_floor"] = perf_trace

        # Layer 9: Confidence Threshold
        min_confidence = self.cfg.min_confidence if self.cfg else 0.6
        confidence_passed = signal.confidence >= min_confidence
        trace["confidence_threshold"] = {
            "passed": bool(confidence_passed),
            "confidence": signal.confidence,
            "min_confidence": min_confidence
        }

        # Layer 10: Signal Consistency (Flicker Guard)
        consistency_passed, consistency_metrics = self._check_signal_consistency_with_metrics(
            signal.symbol, signal.direction
        )
        trace["signal_consistency"] = {
            "passed": bool(consistency_passed),
            **consistency_metrics,
        }

        # Determine final approval
        is_approved = all(t["passed"] for t in trace.values())
        blocked_by = None
        if not is_approved:
            # Order of precedence for blocked_by
            failure_order = [
                ("atr_volatility", "ATR_VOLATILITY"),
                ("trend_angle", "TREND_ANGLE"),
                ("ema_sequence", "EMA_SEQUENCE"),
                ("momentum", "MOMENTUM"),
                ("session_time", "SESSION_CLOSED"),
                ("drawdown_limit", "DRAWDOWN_LIMIT"),
                ("model_stability", "MODEL_STABILITY"),
                ("performance_floor", "PERFORMANCE_FLOOR"),
                ("confidence_threshold", "CONFIDENCE_THRESHOLD"),
                ("signal_consistency", "SIGNAL_CONSISTENCY"),
            ]
            for layer_key, reason in failure_order:
                if not trace[layer_key]["passed"]:
                    blocked_by = reason
                    break

        return ExecutionDecision(
            signal=signal,
            is_approved=is_approved,
            confidence_score=signal.confidence,
            blocked_by=blocked_by,
            trace=trace,
        )

    def _check_atr_volatility(self, df: pd.DataFrame, threshold: float = 3.0) -> bool:
        passed, _ = self._check_atr_volatility_with_metrics(df, threshold)
        return bool(passed)

    def _check_atr_volatility_with_metrics(
        self,
        df: pd.DataFrame,
        threshold: float = 3.0,
        precomputed: dict[str, Any] | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """Blocks if current ATR is > threshold * average ATR."""
        if precomputed:
            current_atr = precomputed.get("current_atr", 0.0)
            avg_atr = precomputed.get("avg_atr", 1.0)
        else:
            if "base_M5_atr" in df.columns:
                atr = df["base_M5_atr"]
            elif "atr" in df.columns:
                atr = df["atr"]
            else:
                if len(df) < 15:
                    return True, {"current_atr": 0.0, "avg_atr": 0.0, "ratio": 0.0}
                high, low, close = df["high"], df["low"], df["close"]
                tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
                atr = tr.rolling(window=14).mean()
            current_atr = float(atr.iloc[-1])
            avg_atr = float(atr.rolling(window=100).mean().iloc[-1])

        if np.isnan(current_atr) or np.isnan(avg_atr) or avg_atr == 0:
            return True, {"current_atr": current_atr, "avg_atr": avg_atr, "ratio": 0.0}

        ratio = current_atr / avg_atr
        passed = ratio <= threshold
        return bool(passed), {"current_atr": current_atr, "avg_atr": avg_atr, "ratio": ratio}

    def _check_trend_angle(self, df: pd.DataFrame, direction: int, window: int = 20) -> bool:
        passed, _ = self._check_trend_angle_with_metrics(df, direction, window)
        return bool(passed)

    def _check_trend_angle_with_metrics(
        self,
        df: pd.DataFrame,
        direction: int,
        window: int = 20,
        precomputed: dict[str, Any] | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """Validates trend matches signal direction using regression slope of EMA21."""
        if precomputed:
            slope = precomputed.get("slope", 0.0)
        else:
            ema_col = "base_M5_ema_21"
            if ema_col in df.columns:
                ema_series = df[ema_col]
            elif "close" in df.columns:
                ema_series = df["close"].iloc[-(window + 50) :].ewm(span=21, adjust=False).mean()
            else:
                return True, {"slope": 0.0, "reason": "No data"}
            target_ema = ema_series.iloc[-window:]
            if len(target_ema) < window:
                return True, {"slope": 0.0, "reason": "Insufficient data"}
            x = np.arange(len(target_ema))
            slope, _, _, _, _ = stats.linregress(x, target_ema.values)

        passed = (direction > 0 and slope > 0) or (direction < 0 and slope < 0)
        return bool(passed), {"slope": float(slope), "direction": direction}

    def _check_ema_sequence(self, df: pd.DataFrame, direction: int) -> bool:
        passed, _ = self._check_ema_sequence_with_metrics(df, direction)
        return bool(passed)

    def _check_ema_sequence_with_metrics(
        self,
        df: pd.DataFrame,
        direction: int,
        precomputed: dict[str, Any] | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """Verifies EMA stack (8 > 21 > 50 > 200 for BUY)."""
        if precomputed:
            emas = precomputed.get("emas", {})
        else:
            periods = [8, 21, 50, 200]
            emas = {}
            for p in periods:
                col = f"base_M5_ema_{p}"
                if col in df.columns:
                    emas[p] = float(df[col].iloc[-1])
                else:
                    emas[p] = float(df["close"].iloc[-300:].ewm(span=p, adjust=False).mean().iloc[-1])

        if direction > 0:
            passed = bool(emas[8] > emas[21] > emas[50] > emas[200])
        elif direction < 0:
            passed = bool(emas[8] < emas[21] < emas[50] < emas[200])
        else:
            passed = False
        return bool(passed), {"emas": emas, "direction": direction}

    def _check_momentum(self, df: pd.DataFrame, direction: int) -> bool:
        passed, _ = self._check_momentum_with_metrics(df, direction)
        return bool(passed)

    def _check_momentum_with_metrics(
        self,
        df: pd.DataFrame,
        direction: int,
        precomputed: dict[str, Any] | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """Validates RSI in healthy zones: BUY (50-75), SELL (25-50)."""
        if precomputed:
            rsi = precomputed.get("rsi", 0.0)
        else:
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
            return True, {"rsi": 50.0}
        passed = (direction > 0 and 50 <= rsi <= 75) or (direction < 0 and 25 <= rsi <= 50)
        return bool(passed), {"rsi": rsi, "direction": direction}

    def _check_session_time(self, timestamp: datetime) -> bool:
        """Blocks outside institutional hours (Sun 17:00 - Fri 16:00 GMT)."""
        wd, hr = timestamp.weekday(), timestamp.hour
        if wd == 5:
            return False
        if wd == 6:
            return hr >= 17
        if wd == 4:
            return hr < 16
        return True

    def _check_drawdown_limit(self, current_drawdown: float) -> bool:
        return current_drawdown < self.max_drawdown

    def _check_signal_consistency_with_metrics(
        self, symbol: str, direction: int
    ) -> tuple[bool, dict[str, Any]]:
        window = self.cfg.signal_flicker_window if self.cfg else 6
        max_changes = self.cfg.max_signal_changes if self.cfg else 3
        if symbol not in self._signal_history:
            self._signal_history[symbol] = deque(maxlen=window)
        history = self._signal_history[symbol]
        history.append(int(direction))
        if len(history) < 2:
            return True, {"changes": 0, "window": window, "max_changes": max_changes}
        changes = 0
        h_list = list(history)
        for i in range(1, len(h_list)):
            if h_list[i] != h_list[i - 1]:
                changes += 1
        passed = changes <= max_changes
        return bool(passed), {"changes": changes, "window": window, "max_changes": max_changes, "history": h_list}
