"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/execution_filter.py
Institutional-grade execution filter implementing a 6-layer validation cascade.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, time
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
        """Returns True if the signal passed all filters."""
        return self.blocked_by is None


class ExecutionFilter:
    """
    6-layer execution filter cascade for institutional-grade trade validation.
    Layers:
    1. ATR Volatility Threshold
    2. Trend Angle Confirmation
    3. EMA Sequence Check
    4. Momentum Filter (RSI)
    5. Session/Time Filter
    6. Drawdown Circuit Breaker
    """

    def validate(
        self,
        signal: TradeSignal,
        market_data: pd.DataFrame,
        current_drawdown: float,
    ) -> ExecutionDecision:
        """
        Run the full 6-layer validation cascade.
        Args:
            signal: The candidate trade signal.
            market_data: Recent OHLCV and indicator data (must include ATR, EMA_20, EMA_50, EMA_200, RSI, ATR_SMA_30).
            current_drawdown: Current account drawdown (0.0 to 1.0).
        Returns:
            ExecutionDecision: Result of the validation.
        """
        # Layer 1: ATR Volatility Threshold
        if not self._check_atr_volatility(market_data):
            return ExecutionDecision(signal, 0.0, "ATR Volatility Threshold exceeded")

        # Layer 2: Trend Angle Confirmation
        if not self._check_trend_angle(signal, market_data):
            return ExecutionDecision(signal, 0.2, "Trend Angle alignment failed")

        # Layer 3: EMA Sequence Check
        if not self._check_ema_sequence(signal, market_data):
            return ExecutionDecision(signal, 0.4, "EMA Sequence misalignment")

        # Layer 4: Momentum Filter
        if not self._check_momentum(signal, market_data):
            return ExecutionDecision(signal, 0.5, "Momentum Filter failed (RSI)")

        # Layer 5: Session/Time Filter
        if not self._check_session_time(signal.timestamp):
            return ExecutionDecision(signal, 0.6, "Prohibited trading hours")

        # Layer 6: Drawdown Circuit Breaker
        if not self._check_drawdown_limit(current_drawdown):
            return ExecutionDecision(signal, 0.0, "Drawdown Circuit Breaker active")

        return ExecutionDecision(signal, signal.confidence)

    def _check_atr_volatility(self, data: pd.DataFrame, multiplier: float = 3.0) -> bool:
        """
        Layer 1: Verify 14-period ATR is not exceeding multiplier * 30-period average ATR.
        """
        if data.empty or "ATR" not in data.columns or "ATR_SMA_30" not in data.columns:
            return False

        last_atr = data["ATR"].iloc[-1]
        avg_atr = data["ATR_SMA_30"].iloc[-1]

        if avg_atr == 0:
            return False

        return last_atr <= (multiplier * avg_atr)

    def _check_trend_angle(self, signal: TradeSignal, data: pd.DataFrame) -> bool:
        """
        Layer 2: Confirm the EMA_20 slope aligns with the signal direction.
        Positive slope for Buy (+1), Negative slope for Sell (-1).
        """
        if data.empty or "EMA_20" not in data.columns or len(data) < 2:
            return False

        slope = data["EMA_20"].iloc[-1] - data["EMA_20"].iloc[-2]

        if signal.direction == 1:
            return slope > 0
        elif signal.direction == -1:
            return slope < 0

        return False

    def _check_ema_sequence(self, signal: TradeSignal, data: pd.DataFrame) -> bool:
        """
        Layer 3: Verify institutional EMA alignment.
        Buy: EMA_20 > EMA_50 > EMA_200
        Sell: EMA_20 < EMA_50 < EMA_200
        """
        cols = ["EMA_20", "EMA_50", "EMA_200"]
        if data.empty or not all(c in data.columns for c in cols):
            return False

        ema20 = data["EMA_20"].iloc[-1]
        ema50 = data["EMA_50"].iloc[-1]
        ema200 = data["EMA_200"].iloc[-1]

        if signal.direction == 1:
            return ema20 > ema50 > ema200
        elif signal.direction == -1:
            return ema20 < ema50 < ema200

        return False

    def _check_momentum(self, signal: TradeSignal, data: pd.DataFrame) -> bool:
        """
        Layer 4: Use RSI to ensure strength without overextension.
        Buy: RSI > 50 and RSI < 70
        Sell: RSI < 50 and RSI > 30
        """
        if data.empty or "RSI" not in data.columns:
            return False

        rsi = data["RSI"].iloc[-1]

        if signal.direction == 1:
            return 50 < rsi < 70
        elif signal.direction == -1:
            return 30 < rsi < 50

        return False

    def _check_session_time(self, ts: datetime) -> bool:
        """
        Layer 5: Enforce XAUUSD hours (Sunday 17:00 - Friday 16:00 GMT).
        Avoid low liquidity: Friday 14:00-16:00 GMT.
        """
        # Day of week: 0=Monday, 4=Friday, 6=Sunday
        weekday = ts.weekday()
        current_time = ts.time()

        # Friday after 14:00 GMT (Low liquidity / Close)
        if weekday == 4 and current_time >= time(14, 0):
            return False

        # Saturday (Closed)
        if weekday == 5:
            return False

        # Sunday before 17:00 GMT (Closed)
        if weekday == 6 and current_time < time(17, 0):
            return False

        return True

    def _check_drawdown_limit(self, current_drawdown: float, max_dd: float = 0.25) -> bool:
        """
        Layer 6: Block if current account drawdown exceeds the hard limit.
        """
        return current_drawdown < max_dd
