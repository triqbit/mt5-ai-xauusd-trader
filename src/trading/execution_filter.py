"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/execution_filter.py
6-layer entry filter cascade to vet signals before execution.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

import numpy as np
import pandas as pd
from scipy import stats

if TYPE_CHECKING:
    from src.trading.risk_manager import TradeSignal

logger = logging.getLogger(__name__)


@dataclass
class ExecutionDecision:
    """Result of the execution filter cascade."""

    signal: TradeSignal
    is_approved: bool
    confidence_score: float
    blocked_by: Optional[str] = None


class ExecutionFilter:
    """
    Implements a 6-layer validation cascade for trading signals.
    Layers: ATR, Trend Angle, EMA Sequence, Momentum, Session, Drawdown.
    """

    def __init__(self, max_drawdown: float = 0.15, rsi_period: int = 14):
        self.max_drawdown = max_drawdown
        self.rsi_period = rsi_period

    def validate(
        self,
        signal: TradeSignal,
        market_data: pd.DataFrame,
        current_drawdown: float,
        timestamp: Optional[datetime] = None,
    ) -> ExecutionDecision:
        """
        Run the full 6-layer filter cascade.
        """
        timestamp = timestamp or signal.timestamp or datetime.now(timezone.utc)

        # Layer 1: ATR Volatility
        if not self._check_atr_volatility(market_data):
            return ExecutionDecision(signal, False, 0.0, "ATR_VOLATILITY")

        # Layer 2: Trend Angle
        if not self._check_trend_angle(market_data, signal.direction):
            return ExecutionDecision(signal, False, 0.2, "TREND_ANGLE")

        # Layer 3: EMA Sequence
        if not self._check_ema_sequence(market_data, signal.direction):
            return ExecutionDecision(signal, False, 0.3, "EMA_SEQUENCE")

        # Layer 4: Momentum (RSI)
        if not self._check_momentum(market_data, signal.direction):
            return ExecutionDecision(signal, False, 0.4, "MOMENTUM")

        # Layer 5: Session/Time
        if not self._check_session_time(timestamp):
            return ExecutionDecision(signal, False, 0.5, "SESSION_TIME")

        # Layer 6: Drawdown
        if not self._check_drawdown_limit(current_drawdown):
            return ExecutionDecision(signal, False, 0.1, "DRAWDOWN_LIMIT")

        return ExecutionDecision(signal, True, signal.confidence)

    def _check_atr_volatility(self, df: pd.DataFrame, threshold: float = 3.0) -> bool:
        """Blocks if current ATR is > threshold * average ATR."""
        if "base_M5_atr" not in df.columns:
            # Fallback calculation if not in DF
            high = df["high"]
            low = df["low"]
            close = df["close"]
            tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
            atr = tr.rolling(window=14).mean()
        else:
            atr = df["base_M5_atr"]

        current_atr = atr.iloc[-1]
        avg_atr = atr.rolling(window=100).mean().iloc[-1]

        if np.isnan(current_atr) or np.isnan(avg_atr):
            return True  # Not enough data, pass

        return bool(current_atr <= threshold * avg_atr)

    def _check_trend_angle(self, df: pd.DataFrame, direction: int, window: int = 20) -> bool:
        """Validates that the price trend matches signal direction using regression slope."""
        close = df["close"].iloc[-window:]
        x = np.arange(len(close))
        slope, _, _, _, _ = stats.linregress(x, close.values)

        if direction > 0:  # BUY
            return bool(slope > 0)
        elif direction < 0:  # SELL
            return bool(slope < 0)
        return False

    def _check_ema_sequence(self, df: pd.DataFrame, direction: int) -> bool:
        """Verifies EMA stack (8 > 21 > 50 > 200 for BUY)."""
        periods = [8, 21, 50, 200]
        emas = {}

        for p in periods:
            col = f"base_M5_ema_{p}"
            if col in df.columns:
                emas[p] = df[col].iloc[-1]
            else:
                emas[p] = df["close"].ewm(span=p, adjust=False).mean().iloc[-1]

        if direction > 0:  # BUY
            return bool(emas[8] > emas[21] > emas[50] > emas[200])
        elif direction < 0:  # SELL
            return bool(emas[8] < emas[21] < emas[50] < emas[200])
        return False

    def _check_momentum(self, df: pd.DataFrame, direction: int) -> bool:
        """Validates RSI is in a healthy momentum zone."""
        col = "base_M5_rsi"
        if col in df.columns:
            rsi = df[col].iloc[-1]
        else:
            delta = df["close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
            rs = gain / (loss + 1e-8)
            rsi = 100 - (100 / (1 + rs)).iloc[-1]

        if np.isnan(rsi):
            return True

        if direction > 0:  # BUY
            return bool(50 <= rsi <= 75)
        elif direction < 0:  # SELL
            return bool(25 <= rsi <= 50)
        return False

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
