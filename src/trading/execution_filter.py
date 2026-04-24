"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/execution_filter.py
6-layer execution validation cascade.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

from src.trading.risk_manager import TradeSignal

logger = logging.getLogger(__name__)


@dataclass
class ExecutionDecision:
    """Outcome of the execution filter validation."""

    signal: TradeSignal
    confidence: float
    is_approved: bool
    blocked_by: Optional[str] = None


class ExecutionFilter:
    """
    Implements a 6-layer validation cascade for trade signals.
    """

    def __init__(self, drawdown_threshold: float = 0.15) -> None:
        self.drawdown_threshold = drawdown_threshold

    def validate(
        self,
        signal: TradeSignal,
        indicators: pd.DataFrame,
        current_drawdown: float,
        timestamp: Optional[datetime] = None,
    ) -> ExecutionDecision:
        """
        Run the full 6-layer validation cascade.
        """
        if indicators.empty:
            return ExecutionDecision(
                signal=signal,
                confidence=0.0,
                is_approved=False,
                blocked_by="Missing indicator data",
            )

        last_row = indicators.iloc[-1]
        ts = timestamp or datetime.now(timezone.utc)

        # Layer 1: ATR Volatility Block
        if not self._validate_volatility(last_row):
            return ExecutionDecision(
                signal=signal,
                confidence=signal.confidence * 0.8,
                is_approved=False,
                blocked_by="Volatility: ATR too high",
            )

        # Layer 2: Trend Angle (EMA 50 slope)
        if not self._validate_trend_angle(indicators, signal.direction):
            return ExecutionDecision(
                signal=signal,
                confidence=signal.confidence * 0.7,
                is_approved=False,
                blocked_by="Trend: EMA50 slope mismatch",
            )

        # Layer 3: EMA Sequence
        if not self._validate_ema_sequence(last_row, signal.direction):
            return ExecutionDecision(
                signal=signal,
                confidence=signal.confidence * 0.6,
                is_approved=False,
                blocked_by="Trend: EMA sequence mismatch",
            )

        # Layer 4: Momentum (RSI)
        if not self._validate_momentum(last_row, signal.direction):
            return ExecutionDecision(
                signal=signal,
                confidence=signal.confidence * 0.5,
                is_approved=False,
                blocked_by="Momentum: RSI mismatch",
            )

        # Layer 5: Session Filter
        if not self._validate_session(ts):
            return ExecutionDecision(
                signal=signal,
                confidence=signal.confidence * 0.9,
                is_approved=False,
                blocked_by="Session: Outside market hours",
            )

        # Layer 6: Drawdown Circuit Breaker
        if not self._validate_drawdown(current_drawdown):
            return ExecutionDecision(
                signal=signal,
                confidence=0.0,
                is_approved=False,
                blocked_by="Risk: Drawdown circuit breaker",
            )

        return ExecutionDecision(
            signal=signal,
            confidence=signal.confidence,
            is_approved=True,
        )

    def _validate_volatility(self, row: pd.Series) -> bool:
        """ATR(14) > 3x MA(100) volatility block."""
        atr = row.get("atr_14")
        atr_ma = row.get("atr_14_ma_100")
        if atr is None or atr_ma is None:
            return True
        return atr <= (3 * atr_ma)

    def _validate_trend_angle(self, df: pd.DataFrame, direction: int) -> bool:
        """50-period EMA slope confirmation."""
        if len(df) < 2 or "ema_50" not in df.columns:
            return True
        ema50_curr = df["ema_50"].iloc[-1]
        ema50_prev = df["ema_50"].iloc[-2]

        if direction > 0:  # Buy
            return ema50_curr > ema50_prev
        elif direction < 0:  # Sell
            return ema50_curr < ema50_prev
        return False

    def _validate_ema_sequence(self, row: pd.Series, direction: int) -> bool:
        """EMA(20) > EMA(50) > EMA(200) for Buy, reverse for Sell."""
        e20 = row.get("ema_20")
        e50 = row.get("ema_50")
        e200 = row.get("ema_200")

        if e20 is None or e50 is None or e200 is None:
            return True

        if direction > 0:
            return e20 > e50 > e200
        elif direction < 0:
            return e20 < e50 < e200
        return False

    def _validate_momentum(self, row: pd.Series, direction: int) -> bool:
        """RSI(14) > 50 (Buy) / < 50 (Sell)."""
        rsi = row.get("rsi_14")
        if rsi is None:
            return True

        if direction > 0:
            return rsi > 50
        elif direction < 0:
            return rsi < 50
        return False

    def _validate_session(self, ts: datetime) -> bool:
        """Institutional 08:00-21:00 GMT session filter."""
        # Ensure we are working with UTC
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = ts.astimezone(timezone.utc)

        hour = ts.hour
        return 8 <= hour < 21

    def _validate_drawdown(self, current_drawdown: float) -> bool:
        """15% drawdown circuit breaker."""
        return current_drawdown < self.drawdown_threshold
