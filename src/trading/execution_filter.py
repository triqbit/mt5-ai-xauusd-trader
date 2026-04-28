"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/execution_filter.py
Institutional 6-layer execution filter cascade.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import time, timezone
from typing import Optional

import pandas as pd

from src.trading.risk_manager import TradeSignal

logger = logging.getLogger(__name__)


@dataclass
class ExecutionDecision:
    """Outcome of the execution filter cascade."""

    signal: TradeSignal
    confidence_score: float
    blocked_by: Optional[str] = None

    @property
    def is_allowed(self) -> bool:
        """Returns True if no filter blocked the signal."""
        return self.blocked_by is None


class ExecutionFilter:
    """
    Institutional 6-layer execution filter.
    Validates signals against volatility, trend, momentum, time, and risk constraints.
    """

    def validate(
        self,
        signal: TradeSignal,
        data: pd.DataFrame,
        current_drawdown: float
    ) -> ExecutionDecision:
        """
        Run the full 6-layer filter cascade.
        Args:
            signal: The TradeSignal to validate.
            data: DataFrame containing OHLCV and indicators (ATR, EMA_20, EMA_50, EMA_200, RSI).
            current_drawdown: Current account drawdown (0.0 to 1.0).
        Returns:
            ExecutionDecision object.
        """
        # 1. ATR Volatility Threshold
        if not self._check_atr_volatility(data):
            return ExecutionDecision(signal, signal.confidence * 0.8, "ATR_VOLATILITY")

        # 2. Trend Angle Confirmation
        if not self._check_trend_angle(signal, data):
            return ExecutionDecision(signal, signal.confidence * 0.7, "TREND_ANGLE")

        # 3. EMA Sequence Check
        if not self._check_ema_sequence(signal, data):
            return ExecutionDecision(signal, signal.confidence * 0.6, "EMA_SEQUENCE")

        # 4. Momentum Filter
        if not self._check_momentum(signal, data):
            return ExecutionDecision(signal, signal.confidence * 0.5, "MOMENTUM")

        # 5. Session/Time Filter
        if not self._check_session(signal):
            return ExecutionDecision(signal, signal.confidence * 0.9, "SESSION_CLOSED")

        # 6. Drawdown Circuit Breaker
        if not self._check_drawdown(current_drawdown):
            return ExecutionDecision(signal, 0.0, "DRAWDOWN_LIMIT")

        return ExecutionDecision(signal, signal.confidence)

    def _check_atr_volatility(self, data: pd.DataFrame, window: int = 30) -> bool:
        """ATR < 3x historical average to avoid extreme volatility spikes."""
        if "ATR" not in data.columns:
            logger.warning("ATR column missing from data")
            return True

        current_atr = data["ATR"].iloc[-1]
        atr_sma = data["ATR"].rolling(window=window).mean().iloc[-1]

        if pd.isna(atr_sma):
            return True # Not enough data to block

        return current_atr < (3 * atr_sma)

    def _check_trend_angle(self, signal: TradeSignal, data: pd.DataFrame) -> bool:
        """EMA_50 slope must align with trade direction."""
        if "EMA_50" not in data.columns or len(data) < 2:
            return True

        current_ema50 = data["EMA_50"].iloc[-1]
        prev_ema50 = data["EMA_50"].iloc[-2]

        if signal.direction > 0: # Buy
            return current_ema50 > prev_ema50
        elif signal.direction < 0: # Sell
            return current_ema50 < prev_ema50

        return False

    def _check_ema_sequence(self, signal: TradeSignal, data: pd.DataFrame) -> bool:
        """EMA 20 > 50 > 200 for Buy, reversed for Sell."""
        cols = ["EMA_20", "EMA_50", "EMA_200"]
        if not all(c in data.columns for c in cols):
            return True

        ema20 = data["EMA_20"].iloc[-1]
        ema50 = data["EMA_50"].iloc[-1]
        ema200 = data["EMA_200"].iloc[-1]

        if signal.direction > 0: # Buy
            return ema20 > ema50 > ema200
        elif signal.direction < 0: # Sell
            return ema20 < ema50 < ema200

        return False

    def _check_momentum(self, signal: TradeSignal, data: pd.DataFrame) -> bool:
        """RSI > 50 for Buy, < 50 for Sell."""
        if "RSI" not in data.columns:
            return True

        rsi = data["RSI"].iloc[-1]

        if signal.direction > 0: # Buy
            return rsi > 50
        elif signal.direction < 0: # Sell
            return rsi < 50

        return False

    def _check_session(self, signal: TradeSignal) -> bool:
        """Trade only between 08:00 and 21:00 GMT."""
        # Convert timestamp to GMT if it's not already
        ts = signal.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = ts.astimezone(timezone.utc)

        current_time = ts.time()
        start_time = time(8, 0)
        end_time = time(21, 0)

        return start_time <= current_time <= end_time

    def _check_drawdown(self, current_drawdown: float, limit: float = 0.15) -> bool:
        """Block if account drawdown exceeds limit."""
        return current_drawdown < limit
