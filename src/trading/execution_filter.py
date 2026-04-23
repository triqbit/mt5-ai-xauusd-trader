"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/execution_filter.py
6-layer execution filter cascade for institutional-grade trade validation.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, time
from typing import Optional

import pandas as pd

from src.trading.risk_manager import TradeSignal

logger = logging.getLogger(__name__)


@dataclass
class ExecutionDecision:
    """Result of the execution filter validation."""

    signal: TradeSignal
    confidence: float
    blocked_by: Optional[str] = None

    @property
    def approved(self) -> bool:
        return self.blocked_by is None


class ExecutionFilter:
    """
    Implements a 6-layer validation cascade to filter out low-probability or high-risk signals.
    Layers:
        1. ATR Volatility (Volatility spike protection)
        2. Trend Angle (EMA Slope confirmation)
        3. EMA Sequence (Trend alignment)
        4. Momentum Filter (RSI alignment)
        5. Session/Time Filter (Institutional liquidity hours)
        6. Drawdown Circuit Breaker (Equity protection)
    """

    def __init__(self, atr_ma_period: int = 100, atr_multiplier: float = 3.0):
        self.atr_ma_period = atr_ma_period
        self.atr_multiplier = atr_multiplier

    def validate(
        self,
        signal: TradeSignal,
        market_data: pd.DataFrame,
        current_drawdown: float,
        timestamp: Optional[datetime] = None,
    ) -> ExecutionDecision:
        """
        Run the 6-layer filter cascade on a signal.

        Args:
            signal: The candidate trade signal.
            market_data: DataFrame containing OHLCV and pre-calculated indicators.
            current_drawdown: Current account drawdown (0.0 to 1.0).
            timestamp: Optional timestamp for backtesting session validation.

        Returns:
            ExecutionDecision object indicating approval or rejection reason.
        """
        if market_data.empty:
            return ExecutionDecision(signal, 0.0, "Empty market data")

        last_row = market_data.iloc[-1]

        # 1. ATR Volatility Threshold
        if not self._check_atr_volatility(last_row):
            return ExecutionDecision(signal, signal.confidence * 0.8, "ATR Volatility Spike")

        # 2. Trend Angle Confirmation
        if not self._check_trend_angle(market_data, signal.direction):
            return ExecutionDecision(signal, signal.confidence * 0.7, "Trend Angle Mismatch")

        # 3. EMA Sequence Check
        if not self._check_ema_sequence(last_row, signal.direction):
            return ExecutionDecision(signal, signal.confidence * 0.6, "EMA Sequence Mismatch")

        # 4. Momentum Filter
        if not self._check_momentum(last_row, signal.direction):
            return ExecutionDecision(signal, signal.confidence * 0.9, "Momentum Mismatch")

        # 5. Session/Time Filter
        eval_time = timestamp or datetime.now(UTC)
        if not self._check_session_filter(eval_time):
            return ExecutionDecision(signal, signal.confidence * 0.5, "Outside Trading Session")

        # 6. Drawdown Circuit Breaker
        if not self._check_drawdown_limit(current_drawdown):
            return ExecutionDecision(signal, 0.0, "Circuit Breaker Active")

        return ExecutionDecision(signal, signal.confidence)

    def _check_atr_volatility(self, row: pd.Series) -> bool:
        """Blocks if ATR(14) > 3x its moving average."""
        atr = row.get("atr_14", 0.0)
        atr_ma = row.get("atr_14_ma_100", 0.0)
        if atr_ma == 0:
            return True
        return bool(atr <= atr_ma * self.atr_multiplier)

    def _check_trend_angle(self, data: pd.DataFrame, direction: int) -> bool:
        """Confirms EMA(50) slope is positive for Buy (+1), negative for Sell (-1)."""
        if len(data) < 2:
            return True
        ema_50_current = data["ema_50"].iloc[-1]
        ema_50_prev = data["ema_50"].iloc[-2]
        slope = ema_50_current - ema_50_prev

        if direction > 0:
            return bool(slope > 0)
        elif direction < 0:
            return bool(slope < 0)
        return True

    def _check_ema_sequence(self, row: pd.Series, direction: int) -> bool:
        """EMA(20) > EMA(50) > EMA(200) for Buy; reverse for Sell."""
        ema20 = row.get("ema_20", 0.0)
        ema50 = row.get("ema_50", 0.0)
        ema200 = row.get("ema_200", 0.0)

        if ema200 == 0:  # Not enough data for EMA200
            return True

        if direction > 0:
            return bool(ema20 > ema50 > ema200)
        elif direction < 0:
            return bool(ema20 < ema50 < ema200)
        return True

    def _check_momentum(self, row: pd.Series, direction: int) -> bool:
        """RSI(14) > 50 for Buy; < 50 for Sell."""
        rsi = row.get("rsi_14", 50.0)
        if direction > 0:
            return bool(rsi > 50)
        elif direction < 0:
            return bool(rsi < 50)
        return True

    def _check_session_filter(self, current_time: datetime) -> bool:
        """London/New York sessions: 08:00 - 21:00 GMT."""
        # Note: In a production environment, use pytz for explicit GMT handling.
        # For simplicity, we assume the input datetime is in GMT.
        t = current_time.time()
        start = time(8, 0)
        end = time(21, 0)
        return bool(start <= t <= end)

    def _check_drawdown_limit(self, drawdown: float) -> bool:
        """Blocks if drawdown exceeds 15%."""
        return bool(drawdown < 0.15)
