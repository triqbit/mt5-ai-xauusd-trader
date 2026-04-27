"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/execution_filter.py

Implements a 6-layer execution filter cascade to validate trading signals
before they reach the order manager.
"""

from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional

import pandas as pd

from src.trading.risk_manager import TradeSignal


@dataclass
class ExecutionDecision:
    """Result of the execution filter validation."""

    signal: TradeSignal
    confidence_score: float
    is_approved: bool
    blocked_by: Optional[str] = None


class ExecutionFilter:
    """
    6-Layer Execution Filter Cascade.
    Validates signals against institutional volatility, trend, momentum,
    and risk parameters.
    """

    def __init__(self, drawdown_pct: float = 0.0):
        self.drawdown_pct = drawdown_pct

    def validate(
        self, signal: TradeSignal, df: pd.DataFrame
    ) -> ExecutionDecision:
        """
        Run the 6-layer filter cascade.
        Args:
            signal: The candidate TradeSignal.
            df: Historical data containing required indicators (EMA, ATR, RSI).
        Returns:
            ExecutionDecision object.
        """
        # 1. Drawdown Circuit Breaker (< 15%)
        if not self._check_drawdown():
            return ExecutionDecision(
                signal=signal,
                confidence_score=signal.confidence,
                is_approved=False,
                blocked_by="Circuit Breaker",
            )

        # 2. Session/Time Filter (08:00 - 21:00 GMT)
        if not self._check_session(signal.timestamp):
            return ExecutionDecision(
                signal=signal,
                confidence_score=signal.confidence,
                is_approved=False,
                blocked_by="Session Filter",
            )

        # 3. ATR Volatility Threshold (< 3x historical average)
        if not self._check_atr(df):
            return ExecutionDecision(
                signal=signal,
                confidence_score=signal.confidence,
                is_approved=False,
                blocked_by="ATR Volatility",
            )

        # 4. Trend Angle Confirmation (EMA 50 slope)
        if not self._check_trend_angle(df, signal.direction):
            return ExecutionDecision(
                signal=signal,
                confidence_score=signal.confidence,
                is_approved=False,
                blocked_by="Trend Angle",
            )

        # 5. EMA Sequence Check (20 > 50 > 200 for Buy)
        if not self._check_ema_sequence(df, signal.direction):
            return ExecutionDecision(
                signal=signal,
                confidence_score=signal.confidence,
                is_approved=False,
                blocked_by="EMA Sequence",
            )

        # 6. Momentum Filter (RSI > 50 for Buy)
        if not self._check_momentum(df, signal.direction):
            return ExecutionDecision(
                signal=signal,
                confidence_score=signal.confidence,
                is_approved=False,
                blocked_by="Momentum Filter",
            )

        return ExecutionDecision(
            signal=signal,
            confidence_score=signal.confidence,
            is_approved=True,
        )

    def _check_drawdown(self) -> bool:
        return self.drawdown_pct < 0.15

    def _check_session(self, timestamp: datetime) -> bool:
        current_time = timestamp.time()
        start = time(8, 0)
        end = time(21, 0)
        return start <= current_time <= end

    def _check_atr(self, df: pd.DataFrame) -> bool:
        if "atr" not in df.columns:
            return False
        current_atr = df["atr"].iloc[-1]
        avg_atr = df["atr"].tail(30).mean()
        return current_atr < (3 * avg_atr)

    def _check_trend_angle(self, df: pd.DataFrame, direction: int) -> bool:
        if "ema_50" not in df.columns:
            return False
        # Calculate slope over last 3 bars
        slope = df["ema_50"].iloc[-1] - df["ema_50"].iloc[-3]
        if direction == 1:  # Buy
            return slope > 0
        if direction == -1:  # Sell
            return slope < 0
        return False

    def _check_ema_sequence(self, df: pd.DataFrame, direction: int) -> bool:
        required = ["ema_20", "ema_50", "ema_200"]
        if not all(col in df.columns for col in required):
            return False

        ema20 = df["ema_20"].iloc[-1]
        ema50 = df["ema_50"].iloc[-1]
        ema200 = df["ema_200"].iloc[-1]

        if direction == 1:  # Buy
            return ema20 > ema50 > ema200
        if direction == -1:  # Sell
            return ema20 < ema50 < ema200
        return False

    def _check_momentum(self, df: pd.DataFrame, direction: int) -> bool:
        if "rsi" not in df.columns:
            return False
        rsi = df["rsi"].iloc[-1]
        if direction == 1:  # Buy
            return rsi > 50
        if direction == -1:  # Sell
            return rsi < 50
        return False
