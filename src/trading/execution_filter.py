"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/execution_filter.py
Institutional 6-layer execution filter cascade.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Optional

import pandas as pd

from src.core.config import TradingConfig
from src.trading.risk_manager import TradeSignal

logger = logging.getLogger(__name__)


@dataclass
class ExecutionDecision:
    """
    Result of the execution filter validation.
    """
    signal: TradeSignal
    confidence_score: float
    is_approved: bool
    blocked_by: Optional[str] = None


class ExecutionFilter:
    """
    Implements a 6-layer validation cascade for trading signals.
    """

    def __init__(self, config: TradingConfig, timeframe: str = "M5") -> None:
        self.cfg = config
        self.timeframe = timeframe
        self.prefix = f"{timeframe}_"

    def validate(
        self, signal: TradeSignal, df: pd.DataFrame, current_drawdown: float
    ) -> ExecutionDecision:
        """
        Run the full 6-layer cascade.
        Returns an ExecutionDecision object.
        """
        # Layer 1: ATR Volatility
        if not self._validate_atr(df):
            return self._reject(signal, "ATR_VOLATILITY")

        # Layer 2: Trend Angle (EMA Slope)
        if not self._validate_trend_angle(df, signal.direction):
            return self._reject(signal, "TREND_ANGLE")

        # Layer 3: EMA Sequence
        if not self._validate_ema_sequence(df, signal.direction):
            return self._reject(signal, "EMA_SEQUENCE")

        # Layer 4: Momentum (RSI)
        if not self._validate_momentum(df, signal.direction):
            return self._reject(signal, "MOMENTUM")

        # Layer 5: Session Filter
        if not self._validate_session():
            return self._reject(signal, "SESSION_FILTER")

        # Layer 6: Drawdown Circuit Breaker
        if not self._validate_drawdown(current_drawdown):
            return self._reject(signal, "DRAWDOWN_CIRCUIT_BREAKER")

        return ExecutionDecision(
            signal=signal,
            confidence_score=signal.confidence,
            is_approved=True
        )

    def _reject(self, signal: TradeSignal, reason: str) -> ExecutionDecision:
        logger.warning("Signal REJECTED by ExecutionFilter | Reason: %s", reason)
        return ExecutionDecision(
            signal=signal,
            confidence_score=signal.confidence,
            is_approved=False,
            blocked_by=reason
        )

    def _validate_atr(self, df: pd.DataFrame) -> bool:
        col = f"{self.prefix}atr_14"
        if col not in df.columns:
            return True
        current_atr = df[col].iloc[-1]
        # Compare current ATR to its 30-period average
        avg_atr = df[col].rolling(30).mean().iloc[-1]
        if pd.isna(avg_atr):
            return True
        return current_atr < 3 * avg_atr

    def _validate_trend_angle(self, df: pd.DataFrame, direction: int) -> bool:
        col = f"{self.prefix}ema_50"
        if col not in df.columns or len(df) < 3:
            return True
        # Slope over last 3 bars
        slope = df[col].iloc[-1] - df[col].iloc[-3]
        if direction > 0:  # BUY
            return slope > 0
        elif direction < 0:  # SELL
            return slope < 0
        return False

    def _validate_ema_sequence(self, df: pd.DataFrame, direction: int) -> bool:
        ema20 = f"{self.prefix}ema_20"
        ema50 = f"{self.prefix}ema_50"
        ema200 = f"{self.prefix}ema_200"

        # If columns missing, skip this layer
        if not all(c in df.columns for c in [ema20, ema50, ema200]):
            return True

        v20 = df[ema20].iloc[-1]
        v50 = df[ema50].iloc[-1]
        v200 = df[ema200].iloc[-1]

        if direction > 0:  # BUY: 20 > 50 > 200
            return v20 > v50 > v200
        elif direction < 0:  # SELL: 20 < 50 < 200
            return v20 < v50 < v200
        return False

    def _validate_momentum(self, df: pd.DataFrame, direction: int) -> bool:
        col = f"{self.prefix}rsi_14"
        if col not in df.columns:
            return True
        rsi = df[col].iloc[-1]
        if direction > 0:  # BUY: RSI should be above 50 (bullish momentum)
            return rsi > 50
        elif direction < 0:  # SELL: RSI should be below 50 (bearish momentum)
            return rsi < 50
        return False

    def _validate_session(self) -> bool:
        # Institutional hours: 08:00 - 21:00 GMT
        now_utc = datetime.now(timezone.utc).time()
        start = time(8, 0)
        end = time(21, 0)
        return start <= now_utc <= end

    def _validate_drawdown(self, current_drawdown: float) -> bool:
        # 15% peak-to-valley drawdown limit
        return current_drawdown < 0.15
