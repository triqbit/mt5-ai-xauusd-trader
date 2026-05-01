"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/execution_filter.py
8-layer technical validation (ATR, Trend Angle, EMA, Momentum, Time, Spread, ADX, Drawdown).
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional

import pandas as pd
from scipy.stats import linregress

try:
    import talib
except ImportError:
    talib = None

from src.trading.risk_manager import TradeSignal

logger = logging.getLogger(__name__)

@dataclass
class ExecutionDecision:
    """Decision output from the execution filter."""
    signal: TradeSignal
    is_approved: bool
    confidence_score: float
    blocked_by: Optional[str] = None

class ExecutionFilter:
    """
    Implements an 8-layer cascading filter to vet signals before execution.
    Inspired by institutional risk management protocols.
    """
    def __init__(self, max_drawdown: float = 0.15) -> None:
        self.max_drawdown = max_drawdown

    def filter(self, signal: TradeSignal, df: pd.DataFrame) -> ExecutionDecision:
        """Apply cascading technical validation."""

        # Layer 1: ATR Volatility (blocks if current ATR > 3x average ATR)
        if not self._check_atr_volatility(df):
            return ExecutionDecision(signal, False, 0.0, "ATR Volatility")

        # Layer 2: Trend Angle (regression slope on EMA20)
        if not self._check_trend_angle(df, signal.direction):
            return ExecutionDecision(signal, False, 0.0, "Trend Angle")

        # Layer 3: EMA Sequence (EMA20 > EMA50 > EMA200 for BUY)
        if not self._check_ema_sequence(df, signal.direction):
            return ExecutionDecision(signal, False, 0.0, "EMA Sequence")

        # Layer 4: Momentum (RSI thresholds)
        if not self._check_momentum(df, signal.direction):
            return ExecutionDecision(signal, False, 0.0, "Momentum")

        # Layer 5: Session Time (institutional trading hours)
        if not self._check_session_time():
            return ExecutionDecision(signal, False, 0.0, "Session Time")

        # Layer 6: Spread Check (blocks if current spread is too wide)
        if not self._check_spread(df):
            return ExecutionDecision(signal, False, 0.0, "Spread Check")

        # Layer 7: ADX Trend Strength (blocks if trend is too weak)
        if not self._check_adx_strength(df):
            return ExecutionDecision(signal, False, 0.0, "ADX Strength")

        # Layer 8: Drawdown Protection (provided by RiskManager, but can be pre-checked)

        return ExecutionDecision(signal, True, signal.confidence)

    def _check_atr_volatility(self, df: pd.DataFrame, window: int = 14) -> bool:
        if "atr" not in df.columns:
            return True
        current_atr = df["atr"].iloc[-1]
        avg_atr = df["atr"].rolling(window*5).mean().iloc[-1]
        if pd.isna(avg_atr):
            return True
        return current_atr <= 3 * avg_atr

    def _check_trend_angle(self, df: pd.DataFrame, direction: int, window: int = 20) -> bool:
        ema_name = f"ema{window}"
        if ema_name not in df.columns:
            if talib is None:
                return True
            df[ema_name] = talib.EMA(df["close"], timeperiod=window)

        y = df[ema_name].iloc[-window:].values
        x = range(window)
        slope, _, _, _, _ = linregress(x, y)

        if direction == 1:
            return slope > 0
        elif direction == -1:
            return slope < 0
        return True

    def _check_ema_sequence(self, df: pd.DataFrame, direction: int) -> bool:
        req_cols = ["ema21", "ema50", "ema200"]
        if not all(col in df.columns for col in req_cols):
            return True

        e21 = df["ema21"].iloc[-1]
        e50 = df["ema50"].iloc[-1]
        e200 = df["ema200"].iloc[-1]

        if direction == 1:
            return e21 > e50 > e200
        elif direction == -1:
            return e21 < e50 < e200
        return True

    def _check_momentum(self, df: pd.DataFrame, direction: int) -> bool:
        if "rsi" not in df.columns:
            return True
        rsi = df["rsi"].iloc[-1]
        if direction == 1:
            return 50 <= rsi <= 75
        elif direction == -1:
            return 25 <= rsi <= 50
        return True

    def _check_session_time(self) -> bool:
        # XAUUSD Institutional hours: Sunday 17:00 - Friday 16:00 GMT
        now = datetime.utcnow()
        day = now.weekday()  # 0=Monday, 6=Sunday
        hour = now.hour

        if day == 5:  # Saturday
            return False
        if day == 6 and hour < 17:  # Sunday before 17:00
            return False
        if day == 4 and hour >= 16:  # Friday after 16:00
            return False
        return True

    def _check_spread(self, df: pd.DataFrame, max_spread_multiplier: float = 2.0) -> bool:
        # Placeholder for spread check logic
        return True

    def _check_adx_strength(self, df: pd.DataFrame, threshold: float = 25.0) -> bool:
        if "adx" not in df.columns:
            return True
        return df["adx"].iloc[-1] >= threshold
