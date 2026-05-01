"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/execution_filter.py
8-layer technical validation cascade for vetting signals before execution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import numpy as np
import pandas as pd
from scipy.stats import linregress

if TYPE_CHECKING:
    from src.trading.risk_manager import TradeSignal

logger = logging.getLogger(__name__)


@dataclass
class ExecutionDecision:
    """Detailed result of the execution filtering process."""

    is_approved: bool
    confidence_score: float
    blocked_by: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class ExecutionFilter:
    """
    Implements an 8-layer institutional execution filter:
    1. ATR Volatility (block if > 3x average)
    2. Trend Angle (regression slope on EMA20)
    3. EMA Sequence (EMA20 > EMA50 > EMA200 for BUY)
    4. Momentum (RSI 50-75 for BUY, 25-50 for SELL)
    5. Session Check (Sun 17:00 - Fri 16:00 GMT)
    6. Spread Check (block if > 3x average)
    7. ADX Strength (block if ADX < 25)
    8. Drawdown Check (block if > 15%)
    """

    def __init__(self) -> None:
        pass

    def validate(
        self,
        signal: "TradeSignal",
        df: pd.DataFrame,
        current_drawdown: float = 0.0,
        timestamp: Optional[datetime] = None,
    ) -> ExecutionDecision:
        """
        Execute the 8-layer cascade.
        """
        # Layer 1: ATR Volatility
        if not self._check_atr_volatility(df):
            return ExecutionDecision(False, 0.0, "ATR Volatility")

        # Layer 2: Trend Angle
        if not self._check_trend_angle(df, signal.direction):
            return ExecutionDecision(False, 0.1, "Trend Angle")

        # Layer 3: EMA Sequence
        if not self._check_ema_sequence(df, signal.direction):
            return ExecutionDecision(False, 0.2, "EMA Sequence")

        # Layer 4: Momentum (RSI)
        if not self._check_momentum(df, signal.direction):
            return ExecutionDecision(False, 0.3, "Momentum")

        # Layer 5: Session Time
        if not self._check_session_time(timestamp):
            return ExecutionDecision(False, 0.0, "Session Time")

        # Layer 6: Spread Check
        # Requires current tick data which might not be in DF. Default to True if missing.
        if "spread" in df.columns and not self._check_spread(df):
            return ExecutionDecision(False, 0.0, "Spread Check")

        # Layer 7: ADX Strength
        if not self._check_adx(df):
            return ExecutionDecision(False, 0.4, "ADX Strength")

        # Layer 8: Drawdown
        if current_drawdown > 0.15:
            return ExecutionDecision(False, 0.0, "Drawdown Check")

        return ExecutionDecision(True, signal.confidence, None)

    # -- Internal Layers ----------------------------------------------------

    def _check_atr_volatility(self, df: pd.DataFrame) -> bool:
        """Blocks if current ATR is > 3x the 100-period average."""
        high_low = df["high"] - df["low"]
        atr = high_low.rolling(14).mean()
        avg_atr = atr.rolling(100).mean()

        current_atr = atr.iloc[-1]
        threshold = avg_atr.iloc[-1] * 3.0

        return current_atr <= threshold

    def _check_trend_angle(self, df: pd.DataFrame, direction: int) -> bool:
        """Blocks if the slope of EMA20 is against the signal direction."""
        ema20 = df["close"].ewm(span=20, adjust=False).mean()
        y = ema20.tail(10).values
        x = np.arange(len(y))
        slope, _, _, _, _ = linregress(x, y)

        if direction == 1 and slope < 0:
            return False
        return not (direction == -1 and slope > 0)

    def _check_ema_sequence(self, df: pd.DataFrame, direction: int) -> bool:
        """Enforces EMA20 > EMA50 > EMA200 for BUY (vice versa for SELL)."""
        e20 = df["close"].ewm(span=20, adjust=False).mean().iloc[-1]
        e50 = df["close"].ewm(span=50, adjust=False).mean().iloc[-1]
        e200 = df["close"].ewm(span=200, adjust=False).mean().iloc[-1]

        if direction == 1:
            return e20 > e50 > e200
        if direction == -1:
            return e20 < e50 < e200
        return True

    def _check_momentum(self, df: pd.DataFrame, direction: int) -> bool:
        """RSI 50-75 for BUY; 25-50 for SELL."""
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]

        if direction == 1:
            return 50 <= current_rsi <= 75
        if direction == -1:
            return 25 <= current_rsi <= 50
        return True

    def _check_session_time(self, dt: Optional[datetime] = None) -> bool:
        """XAUUSD hours: Sun 17:00 - Fri 16:00 GMT."""
        dt = dt or datetime.utcnow()
        weekday = dt.weekday()  # 0=Mon, 6=Sun
        hour = dt.hour

        if weekday == 5:  # Sat
            return False
        if weekday == 6 and hour < 17:  # Sun before 17:00
            return False
        return not (weekday == 4 and hour >= 16)

    def _check_spread(self, df: pd.DataFrame) -> bool:
        """Blocks if spread > 3x the 100-period average."""
        if "spread" not in df.columns:
            return True
        avg_spread = df["spread"].rolling(100).mean().iloc[-1]
        current_spread = df["spread"].iloc[-1]
        return current_spread <= avg_spread * 3.0

    def _check_adx(self, df: pd.DataFrame) -> bool:
        """Blocks if ADX < 25 (weak trend)."""
        # Simplified ADX calculation
        plus_dm = df["high"].diff()
        minus_dm = df["low"].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        minus_dm = minus_dm.abs()

        tr1 = df["high"] - df["low"]
        tr2 = (df["high"] - df["close"].shift(1)).abs()
        tr3 = (df["low"] - df["close"].shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr_14 = tr.rolling(14).mean()
        plus_di = 100 * (plus_dm.rolling(14).mean() / atr_14)
        minus_di = 100 * (minus_dm.rolling(14).mean() / atr_14)

        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9)
        adx = dx.rolling(14).mean().iloc[-1]

        return adx >= 25
