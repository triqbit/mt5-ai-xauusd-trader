"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/execution_filter.py
6-layer execution filter cascade for signal validation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ExecutionDecision:
    """Outcome of the execution filter cascade."""

    signal: int  # 1: Buy, -1: Sell, 0: Blocked/Hold
    confidence_score: float
    blocked_by: Optional[str] = None


class ExecutionFilter:
    """
    Implements a 6-layer validation cascade:
    1. ATR Volatility
    2. Trend Angle
    3. EMA Sequence
    4. Momentum Filter
    5. Session/Time Filter
    6. Drawdown Circuit Breaker
    """

    def __init__(
        self,
        atr_period: int = 14,
        atr_avg_period: int = 30,
        ema_fast: int = 20,
        ema_med: int = 50,
        ema_slow: int = 200,
        rsi_period: int = 14,
        drawdown_limit: float = 0.15,
    ):
        self.atr_period = atr_period
        self.atr_avg_period = atr_avg_period
        self.ema_fast = ema_fast
        self.ema_med = ema_med
        self.ema_slow = ema_slow
        self.rsi_period = rsi_period
        self.drawdown_limit = drawdown_limit

    def validate(
        self,
        df: pd.DataFrame,
        signal: int,
        confidence: float,
        drawdown: float,
        timestamp: Optional[datetime] = None,
    ) -> ExecutionDecision:
        """
        Runs the full 6-layer cascade.
        """
        if signal == 0:
            return ExecutionDecision(signal=0, confidence_score=confidence)

        # 1. ATR Volatility
        if not self._check_atr_volatility(df):
            return ExecutionDecision(
                signal=0, confidence_score=confidence, blocked_by="ATR_VOLATILITY"
            )

        # 2. Trend Angle (Confirmation)
        if not self._check_trend_angle(df, signal):
            return ExecutionDecision(
                signal=0, confidence_score=confidence, blocked_by="TREND_ANGLE"
            )

        # 3. EMA Sequence
        if not self._check_ema_sequence(df, signal):
            return ExecutionDecision(
                signal=0, confidence_score=confidence, blocked_by="EMA_SEQUENCE"
            )

        # 4. Momentum Filter
        if not self._check_momentum(df, signal):
            return ExecutionDecision(signal=0, confidence_score=confidence, blocked_by="MOMENTUM")

        # 5. Session/Time Filter
        if not self._check_session(timestamp):
            return ExecutionDecision(
                signal=0, confidence_score=confidence, blocked_by="SESSION_TIME"
            )

        # 6. Drawdown Circuit Breaker
        if drawdown >= self.drawdown_limit:
            return ExecutionDecision(
                signal=0, confidence_score=confidence, blocked_by="DRAWDOWN_LIMIT"
            )

        return ExecutionDecision(signal=signal, confidence_score=confidence)

    def _check_atr_volatility(self, df: pd.DataFrame) -> bool:
        # Calculate True Range manually to avoid pandas-ta dependency in CI
        high = df["high"]
        low = df["low"]
        close_prev = df["close"].shift(1)
        tr = pd.concat(
            [high - low, (high - close_prev).abs(), (low - close_prev).abs()], axis=1
        ).max(axis=1)
        atr = tr.rolling(window=self.atr_period).mean()

        if atr.empty:
            return False
        current_atr = atr.iloc[-1]
        avg_atr = atr.rolling(window=self.atr_avg_period).mean().iloc[-1]

        if pd.isna(current_atr) or pd.isna(avg_atr):
            return True  # Not enough history yet to block

        return bool(current_atr <= 3 * avg_atr)

    def _check_trend_angle(self, df: pd.DataFrame, signal: int) -> bool:
        ema_med = df["close"].ewm(span=self.ema_med, adjust=False).mean()
        if len(ema_med) < 2:
            return False

        slope = ema_med.iloc[-1] - ema_med.iloc[-2]
        if signal == 1:
            return bool(slope > 0)
        if signal == -1:
            return bool(slope < 0)
        return False

    def _check_ema_sequence(self, df: pd.DataFrame, signal: int) -> bool:
        ema_f = df["close"].ewm(span=self.ema_fast, adjust=False).mean()
        ema_m = df["close"].ewm(span=self.ema_med, adjust=False).mean()
        ema_s = df["close"].ewm(span=self.ema_slow, adjust=False).mean()

        f, m, s = ema_f.iloc[-1], ema_m.iloc[-1], ema_s.iloc[-1]

        if pd.isna(f) or pd.isna(m) or pd.isna(s):
            return False

        if signal == 1:
            return bool(f > m > s)
        if signal == -1:
            return bool(f < m < s)
        return False

    def _check_momentum(self, df: pd.DataFrame, signal: int) -> bool:
        delta = df["close"].diff()
        up = delta.clip(lower=0)
        down = -delta.clip(upper=0)
        ma_up = up.rolling(window=self.rsi_period).mean()
        ma_down = down.rolling(window=self.rsi_period).mean()

        if ma_down.iloc[-1] == 0:
            current_rsi = 100.0 if ma_up.iloc[-1] != 0 else 50.0
        else:
            rs = ma_up.iloc[-1] / ma_down.iloc[-1]
            current_rsi = 100 - (100 / (1 + rs))

        if pd.isna(current_rsi):
            return False

        if signal == 1:
            return bool(current_rsi > 50)
        if signal == -1:
            return bool(current_rsi < 50)
        return False

    def _check_session(self, timestamp: Optional[datetime]) -> bool:
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        # Weekday: 0=Monday, ..., 5=Saturday, 6=Sunday
        return bool(timestamp.weekday() < 5)
