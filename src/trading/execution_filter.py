"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/execution_filter.py
6-layer validation cascade for trade execution.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ExecutionDecision:
    """Typed result of the execution filter cascade."""

    approved: bool
    reason: str
    layers_passed: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExecutionFilter:
    """
    Implements a 6-layer validation cascade:
    1. ATR Volatility (Market Regime)
    2. Trend Angle (Directional Strength)
    3. EMA Sequence (Trend Alignment)
    4. Momentum (Overbought/Oversold)
    5. Session/Time (Liquidity)
    6. Drawdown Circuit Breaker (Risk)
    """

    def __init__(self, config: Any = None) -> None:
        self.cfg = config
        self.max_drawdown_limit = 0.12  # 12% as per README

    def validate(
        self,
        symbol: str,
        direction: int,
        df: pd.DataFrame,
        current_drawdown: float = 0.0,
        timestamp: Optional[datetime] = None,
    ) -> ExecutionDecision:
        """
        Run the cascade. df must contain required indicators.
        Expected columns: 'atr', 'ema_50', 'ema_100', 'ema_200', 'rsi', 'angle'
        """
        if df.empty:
            return ExecutionDecision(False, "Empty data", 0)

        last_row = df.iloc[-1]
        layers_passed = 0

        # Layer 1: ATR Volatility
        # Avoid trading in extremely high or low volatility
        atr = last_row.get("atr", 0)
        atr_sma = df["atr"].rolling(100).mean().iloc[-1] if "atr" in df else 0
        if atr > atr_sma * 2.5 or atr < atr_sma * 0.1:
            return ExecutionDecision(False, f"ATR Volatility: {atr:.4f}", layers_passed)
        layers_passed += 1

        # Layer 2: Trend Angle
        # Check if the trend is strong enough (e.g., > 20 degrees)
        angle = last_row.get("angle", 0)
        if abs(angle) < 15.0:
            return ExecutionDecision(False, f"Trend Angle too flat: {angle:.2f}", layers_passed)
        if direction == 1 and angle < 0:
            return ExecutionDecision(False, "Trend Angle opposes BUY", layers_passed)
        if direction == -1 and angle > 0:
            return ExecutionDecision(False, "Trend Angle opposes SELL", layers_passed)
        layers_passed += 1

        # Layer 3: EMA Sequence
        # BUY: EMA 50 > EMA 100 > EMA 200
        # SELL: EMA 50 < EMA 100 < EMA 200
        ema50 = last_row.get("ema_50")
        ema100 = last_row.get("ema_100")
        ema200 = last_row.get("ema_200")

        if all(x is not None for x in [ema50, ema100, ema200]):
            if direction == 1 and not (ema50 > ema100 > ema200):
                return ExecutionDecision(False, "EMA Sequence invalid for BUY", layers_passed)
            if direction == -1 and not (ema50 < ema100 < ema200):
                return ExecutionDecision(False, "EMA Sequence invalid for SELL", layers_passed)
        layers_passed += 1

        # Layer 4: Momentum (RSI)
        # Avoid buying when overbought, selling when oversold
        rsi = last_row.get("rsi", 50)
        if direction == 1 and rsi > 75:
            return ExecutionDecision(False, f"RSI Overbought: {rsi:.2f}", layers_passed)
        if direction == -1 and rsi < 25:
            return ExecutionDecision(False, f"RSI Oversold: {rsi:.2f}", layers_passed)
        layers_passed += 1

        # Layer 5: Session/Time
        # Avoid illiquid periods (e.g., first and last 30 mins of FX day)
        now = timestamp if timestamp else datetime.now(timezone.utc)
        hour = now.hour
        minute = now.minute
        if (hour == 23 and minute > 30) or (hour == 0 and minute < 30):
            return ExecutionDecision(False, "Restricted Session (Low Liquidity)", layers_passed)
        layers_passed += 1

        # Layer 6: Drawdown Circuit Breaker
        if current_drawdown > self.max_drawdown_limit:
            return ExecutionDecision(
                False, f"Circuit Breaker: Drawdown {current_drawdown:.2%}", layers_passed
            )
        layers_passed += 1

        return ExecutionDecision(
            True,
            "All layers passed",
            layers_passed,
            {"atr": atr, "angle": angle, "rsi": rsi, "drawdown": current_drawdown},
        )
