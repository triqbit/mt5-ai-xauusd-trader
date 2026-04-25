"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/execution_filter.py
Institutional-grade 6-layer entry validation cascade.
Author : triqbit
License: MIT
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
    """Result of the execution filter cascade."""

    signal: TradeSignal
    confidence_score: float
    is_approved: bool
    blocked_by: Optional[str] = None


class ExecutionFilter:
    """
    6-Layer Execution Filter Cascade.
    Validates signals against institutional risk and technical criteria.
    """

    def validate(
        self,
        signal: TradeSignal,
        indicators_df: pd.DataFrame,
        current_drawdown: float,
        timestamp: Optional[datetime] = None,
    ) -> ExecutionDecision:
        """
        Run the full 6-layer validation cascade.
        Returns ExecutionDecision with approval status and rejection reason.
        """
        if indicators_df.empty:
            return ExecutionDecision(signal, 0.0, False, "Empty indicators data")

        # Layer 1: ATR Volatility (ATR(14) <= 3 * ATR_MA(100))
        if not self._validate_atr_volatility(indicators_df):
            return ExecutionDecision(signal, 0.1, False, "ATR Volatility Block")

        # Layer 2: Trend Angle (EMA(50) slope confirmation)
        if not self._validate_trend_angle(signal, indicators_df):
            return ExecutionDecision(signal, 0.2, False, "Trend Angle Mismatch")

        # Layer 3: EMA Sequence (EMA(20) > EMA(50) > EMA(200) for BUY)
        if not self._validate_ema_sequence(signal, indicators_df):
            return ExecutionDecision(signal, 0.3, False, "EMA Sequence Invalid")

        # Layer 4: Momentum Filter (RSI(14) confirmation)
        if not self._validate_momentum(signal, indicators_df):
            return ExecutionDecision(signal, 0.4, False, "Momentum Filter Block")

        # Layer 5: Session Filter (Institutional hours 08:00-21:00 GMT)
        if not self._validate_session(timestamp):
            return ExecutionDecision(signal, 0.5, False, "Outside Trading Session")

        # Layer 6: Drawdown Circuit Breaker (< 15%)
        if not self._validate_drawdown(current_drawdown):
            return ExecutionDecision(signal, 0.6, False, "Drawdown Circuit Breaker")

        return ExecutionDecision(signal, signal.confidence, True)

    # -- Internal Layer Logic -----------------------------------------------

    def _validate_atr_volatility(self, df: pd.DataFrame) -> bool:
        """Blocks if market volatility is 3x higher than 100-period average."""
        if "atr_14" not in df.columns or "atr_14_ma_100" not in df.columns:
            logger.debug("ATR columns missing, skipping ATR volatility check")
            return True
        last_atr = df["atr_14"].iloc[-1]
        atr_ma = df["atr_14_ma_100"].iloc[-1]
        if atr_ma == 0:
            return True
        return last_atr <= 3 * atr_ma

    def _validate_trend_angle(self, signal: TradeSignal, df: pd.DataFrame) -> bool:
        """Ensures the 50-period EMA is sloping in the direction of the trade."""
        if "ema_50" not in df.columns or len(df) < 2:
            logger.debug("EMA 50 or sufficient data missing, skipping trend angle check")
            return True
        slope = df["ema_50"].iloc[-1] - df["ema_50"].iloc[-2]
        if signal.direction == 1:  # Buy
            return slope > 0
        if signal.direction == -1:  # Sell
            return slope < 0
        return False

    def _validate_ema_sequence(self, signal: TradeSignal, df: pd.DataFrame) -> bool:
        """Confirms long-term trend alignment (20 > 50 > 200 for BUY)."""
        cols = ["ema_20", "ema_50", "ema_200"]
        if not all(c in df.columns for c in cols):
            logger.debug("EMA sequence columns missing, skipping sequence check")
            return True
        e20 = df["ema_20"].iloc[-1]
        e50 = df["ema_50"].iloc[-1]
        e200 = df["ema_200"].iloc[-1]

        if signal.direction == 1:
            return e20 > e50 > e200
        if signal.direction == -1:
            return e20 < e50 < e200
        return False

    def _validate_momentum(self, signal: TradeSignal, df: pd.DataFrame) -> bool:
        """Ensures RSI is in the correct half (RSI > 50 for BUY)."""
        if "rsi_14" not in df.columns:
            logger.debug("RSI column missing, skipping momentum check")
            return True
        rsi = df["rsi_14"].iloc[-1]
        if signal.direction == 1:
            return rsi > 50
        if signal.direction == -1:
            return rsi < 50
        return False

    def _validate_session(self, timestamp: Optional[datetime]) -> bool:
        """Restricts trading to institutional GMT hours."""
        now = timestamp or datetime.now(timezone.utc)
        return 8 <= now.hour < 21

    def _validate_drawdown(self, current_drawdown: float) -> bool:
        """Final circuit breaker if account drawdown exceeds 15%."""
        return current_drawdown < 0.15
