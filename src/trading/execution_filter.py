"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/execution_filter.py
6-layer validation cascade for signal execution.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ExecutionDecision:
    """Outcome of the execution filter cascade."""

    approved: bool
    reason: str
    layer: str
    timestamp: datetime


class ExecutionFilter:
    """
    Implements a 6-layer validation cascade for trading signals.
    Layers: Volatility, Trend Angle, EMA Sequence, Momentum, Session, Circuit Breaker.
    """

    def __init__(self, config: Optional[any] = None) -> None:
        self.cfg = config

    def validate(
        self,
        row: pd.Series,
        direction: int,
        timestamp: Optional[datetime] = None,
        current_drawdown: float = 0.0,
        prev_rows: Optional[pd.DataFrame] = None,
    ) -> ExecutionDecision:
        """
        Run the 6-layer cascade using pre-calculated indicators.
        Args:
            row: Current bar data with technical indicators.
            direction: +1 for Buy, -1 for Sell.
            timestamp: Optional bar time (for backtesting).
            current_drawdown: Current account drawdown.
            prev_rows: Optional previous rows for slope calculation.
        Returns:
            ExecutionDecision dataclass.
        """
        ts = timestamp or datetime.utcnow()

        # 1. Volatility Layer (ATR > 3x average)
        if "atr" in row and "avg_atr" in row and row["atr"] > 3 * row["avg_atr"]:
            return ExecutionDecision(False, "Extreme volatility", "Volatility", ts)

        # 2. Trend Angle (EMA 50 slope)
        # Simplified: check if current EMA 50 is above/below EMA 50 from 5 bars ago if available
        if prev_rows is not None and len(prev_rows) >= 5 and "ema_50" in row:
            ema50_prev = prev_rows.iloc[-5]["ema_50"]
            slope = (row["ema_50"] - ema50_prev) / 5
            if direction == 1 and slope < 0:
                return ExecutionDecision(False, "Negative trend angle for BUY", "Trend", ts)
            if direction == -1 and slope > 0:
                return ExecutionDecision(False, "Positive trend angle for SELL", "Trend", ts)

        # 3. EMA Sequence (20 > 50 > 200 for BUY)
        if all(k in row for k in ["ema_20", "ema_50", "ema_200"]):
            if direction == 1 and not (row["ema_20"] > row["ema_50"] > row["ema_200"]):
                return ExecutionDecision(False, "Invalid EMA sequence for BUY", "EMA_Sequence", ts)
            if direction == -1 and not (row["ema_20"] < row["ema_50"] < row["ema_200"]):
                return ExecutionDecision(False, "Invalid EMA sequence for SELL", "EMA_Sequence", ts)

        # 4. Momentum (RSI)
        if "rsi" in row:
            if direction == 1 and row["rsi"] < 50:
                return ExecutionDecision(False, "RSI < 50 for BUY", "Momentum", ts)
            if direction == -1 and row["rsi"] > 50:
                return ExecutionDecision(False, "RSI > 50 for SELL", "Momentum", ts)

        # 5. Session/Time Filter
        hour = ts.hour
        if hour == 23:
            return ExecutionDecision(False, "Market rollover period", "Session", ts)

        # 6. Drawdown Circuit Breaker
        if current_drawdown >= 0.15:
            return ExecutionDecision(False, "Circuit breaker active", "Risk", ts)

        return ExecutionDecision(True, "All layers passed", "Success", ts)


__all__ = ["ExecutionDecision", "ExecutionFilter"]
