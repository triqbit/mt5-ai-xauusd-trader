"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/execution_filter.py
Institutional 6-layer execution filter cascade.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from src.trading.risk_manager import TradeSignal

logger = logging.getLogger(__name__)


@dataclass
class ExecutionDecision:
    """Result of the execution filter validation."""

    signal: TradeSignal
    confidence_score: float
    blocked_by: Optional[str] = None

    @property
    def is_allowed(self) -> bool:
        return self.blocked_by is None


class ExecutionFilter:
    """
    Implements a 6-layer sequential validation for trading signals.
    """

    def validate(
        self,
        signal: TradeSignal,
        market_data: pd.DataFrame,
        current_drawdown: float,
    ) -> ExecutionDecision:
        """
        Run the sequential validation layers.
        """
        # 1. ATR Threshold Layer
        if not self._check_atr_threshold(market_data):
            return ExecutionDecision(signal, signal.confidence, "ATR Threshold")

        # 2. Trend Angle Layer
        if not self._check_trend_angle(signal, market_data):
            return ExecutionDecision(signal, signal.confidence, "Trend Angle")

        # 3. EMA Sequence Layer
        if not self._check_ema_sequence(signal, market_data):
            return ExecutionDecision(signal, signal.confidence, "EMA Sequence")

        # 4. RSI Momentum Layer
        if not self._check_rsi_momentum(signal, market_data):
            return ExecutionDecision(signal, signal.confidence, "RSI Momentum")

        # 5. Session Filter Layer
        if not self._check_session_filter(signal):
            return ExecutionDecision(signal, signal.confidence, "Session Filter")

        # 6. Drawdown Circuit Breaker Layer
        if current_drawdown >= 0.15:  # 15% limit
            return ExecutionDecision(signal, signal.confidence, "Drawdown Circuit Breaker")

        return ExecutionDecision(signal, signal.confidence)

    def _check_atr_threshold(self, df: pd.DataFrame) -> bool:
        """ATR must be within 3x of historical 30-period average."""
        if "atr" not in df.columns:
            return True
        current_atr = df["atr"].iloc[-1]
        avg_atr = df["atr"].rolling(30).mean().iloc[-1]
        if pd.isna(avg_atr):
            return True
        return current_atr <= 3 * avg_atr

    def _check_trend_angle(self, signal: TradeSignal, df: pd.DataFrame) -> bool:
        """EMA 50 slope must align with signal direction."""
        if "ema_50" not in df.columns:
            return True
        ema_50 = df["ema_50"]
        if len(ema_50) < 2:
            return True
        slope = ema_50.iloc[-1] - ema_50.iloc[-2]
        if signal.direction == 1:  # Buy
            return slope > 0
        elif signal.direction == -1:  # Sell
            return slope < 0
        return True

    def _check_ema_sequence(self, signal: TradeSignal, df: pd.DataFrame) -> bool:
        """EMA 20 > 50 > 200 for Buy, vice versa for Sell."""
        cols = ["ema_20", "ema_50", "ema_200"]
        if not all(c in df.columns for c in cols):
            return True
        e20, e50, e200 = df[cols].iloc[-1]
        if signal.direction == 1:
            return e20 > e50 > e200
        elif signal.direction == -1:
            return e20 < e50 < e200
        return True

    def _check_rsi_momentum(self, signal: TradeSignal, df: pd.DataFrame) -> bool:
        """RSI > 50 for Buy, RSI < 50 for Sell."""
        if "rsi" not in df.columns:
            return True
        rsi = df["rsi"].iloc[-1]
        if signal.direction == 1:
            return rsi > 50
        elif signal.direction == -1:
            return rsi < 50
        return True

    def _check_session_filter(self, signal: TradeSignal) -> bool:
        """Restrict trading to 08:00 - 21:00 GMT."""
        hour = signal.timestamp.hour
        return 8 <= hour <= 21

__all__ = ["ExecutionDecision", "ExecutionFilter"]
