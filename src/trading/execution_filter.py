"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/execution_filter.py
6-layer execution filter cascade for signal validation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd

try:
    import pandas_ta as ta  # noqa: F401
    HAS_PANDAS_TA = True
except ImportError:
    HAS_PANDAS_TA = False

try:
    import talib
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False

from src.core.config import TradingConfig

logger = logging.getLogger(__name__)


@dataclass
class ExecutionDecision:
    """Typed result of the execution filter validation."""

    signal: bool
    confidence_score: float
    blocked_by: Optional[str] = None


class ExecutionFilter:
    """
    Validates trading signals through a 6-layer cascade:
    1. ATR Volatility Threshold
    2. Trend Angle Confirmation
    3. EMA Sequence Check
    4. Momentum Filter (RSI)
    5. Session/Time Filter
    6. Drawdown Circuit Breaker
    """

    def __init__(self, config: TradingConfig):
        self.cfg = config
        if not HAS_PANDAS_TA and not HAS_TALIB:
            logger.warning("Neither pandas-ta nor TA-Lib found. Some filters may fail.")

    def validate(
        self,
        df: pd.DataFrame,
        direction: int,
        current_drawdown: float,
        confidence: float,
    ) -> ExecutionDecision:
        """
        Run all 6 filter layers.
        Direction: 1 (Buy), -1 (Sell)
        """
        # 1. ATR Volatility Threshold
        if not self._check_atr_volatility(df):
            return ExecutionDecision(False, confidence, "ATR Volatility Threshold")

        # 2. Trend Angle Confirmation
        if not self._check_trend_angle(df, direction):
            return ExecutionDecision(False, confidence, "Trend Angle")

        # 3. EMA Sequence Check
        if not self._check_ema_sequence(df, direction):
            return ExecutionDecision(False, confidence, "EMA Sequence")

        # 4. Momentum Filter
        if not self._check_momentum(df, direction):
            return ExecutionDecision(False, confidence, "Momentum (RSI)")

        # 5. Session/Time Filter
        if not self._check_session_filter():
            return ExecutionDecision(False, confidence, "Session/Time")

        # 6. Drawdown Circuit Breaker
        if not self._check_drawdown(current_drawdown):
            return ExecutionDecision(False, confidence, "Drawdown Circuit Breaker")

        return ExecutionDecision(True, confidence)

    def _check_atr_volatility(self, df: pd.DataFrame, min_atr: float = 0.5) -> bool:
        """Ensure there is enough volatility to trade."""
        if HAS_PANDAS_TA:
            atr = df.ta.atr(length=14)
        elif HAS_TALIB:
            atr = pd.Series(
                talib.ATR(df["high"], df["low"], df["close"], timeperiod=14),
                index=df.index,
            )
        else:
            return True  # Fallback if no library

        if atr is None or len(atr) == 0:
            return False
        return bool(atr.iloc[-1] > min_atr)

    def _check_trend_angle(self, df: pd.DataFrame, direction: int) -> bool:
        """Confirm trend direction using EMA slope."""
        if HAS_PANDAS_TA:
            ema20 = df.ta.ema(length=20)
        elif HAS_TALIB:
            ema20 = pd.Series(talib.EMA(df["close"], timeperiod=20), index=df.index)
        else:
            return True

        if ema20 is None or len(ema20) < 2:
            return False
        slope = ema20.iloc[-1] - ema20.iloc[-2]
        return bool((direction == 1 and slope > 0) or (direction == -1 and slope < 0))

    def _check_ema_sequence(self, df: pd.DataFrame, direction: int) -> bool:
        """Check for EMA alignment (20 > 50 > 200 for BUY)."""
        if HAS_PANDAS_TA:
            ema20 = df.ta.ema(length=20)
            ema50 = df.ta.ema(length=50)
            ema200 = df.ta.ema(length=200)
        elif HAS_TALIB:
            ema20 = pd.Series(talib.EMA(df["close"], timeperiod=20), index=df.index)
            ema50 = pd.Series(talib.EMA(df["close"], timeperiod=50), index=df.index)
            ema200 = pd.Series(talib.EMA(df["close"], timeperiod=200), index=df.index)
        else:
            return True

        if ema200 is None or len(ema200) == 0 or pd.isna(ema200.iloc[-1]):
            return False

        e20, e50, e200 = ema20.iloc[-1], ema50.iloc[-1], ema200.iloc[-1]

        if direction == 1:  # Buy
            return bool(e20 > e50 > e200)
        elif direction == -1:  # Sell
            return bool(e20 < e50 < e200)
        return False

    def _check_momentum(self, df: pd.DataFrame, direction: int) -> bool:
        """Confirm momentum using RSI."""
        if HAS_PANDAS_TA:
            rsi = df.ta.rsi(length=14)
        elif HAS_TALIB:
            rsi = pd.Series(talib.RSI(df["close"], timeperiod=14), index=df.index)
        else:
            return True

        if rsi is None or len(rsi) == 0 or pd.isna(rsi.iloc[-1]):
            return False

        current_rsi = rsi.iloc[-1]
        if direction == 1:
            return bool(current_rsi > 50)  # Bullish momentum
        elif direction == -1:
            return bool(current_rsi < 50)  # Bearish momentum
        return False

    def _check_session_filter(self) -> bool:
        """
        Validate XAUUSD trading sessions.
        XAUUSD is active 23 hours a day, Monday to Friday.
        Closed 22:00 - 23:00 GMT daily.
        """
        now = datetime.utcnow()
        if now.weekday() >= 5:  # Saturday or Sunday
            return False

        hour = now.hour
        if hour == 22:  # Daily maintenance break
            return False

        return True

    def _check_drawdown(self, current_drawdown: float) -> bool:
        """Block if max drawdown limit reached."""
        # Using 10% as default if not in config
        max_dd = getattr(self.cfg, "max_drawdown", 0.10)
        return bool(current_drawdown < max_dd)
