"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/execution_filter.py
Institutional 6-layer validation cascade for signal execution.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class ExecutionFilter:
    """
    Implements a 6-layer validation cascade for trading signals:
    1. ATR Volatility Block: ATR(14) > 3x MA(100)
    2. EMA Slope Confirmation: 50-period EMA slope
    3. EMA Sequence: EMA(20) > EMA(50) > EMA(200) for BUY (reverse for SELL)
    4. RSI Momentum: RSI(14) > 50 (BUY) / < 50 (SELL)
    5. Institutional Session Filter: 08:00 - 21:00 GMT
    6. Circuit Breaker Check: External check for drawdown limits
    """

    def __init__(self) -> None:
        pass

    def validate(
        self,
        signal_direction: int,
        df_indicators: pd.DataFrame,
        current_drawdown: float,
        timestamp: Optional[datetime] = None,
    ) -> bool:
        """
        Validate a signal against the 6-layer cascade.
        signal_direction: +1 for BUY, -1 for SELL
        df_indicators: DataFrame containing necessary indicators
        current_drawdown: Current account drawdown (0.0 to 1.0)
        timestamp: Current time for session filtering (defaults to UTC now)
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        # Layer 6: Circuit Breaker
        if current_drawdown >= 0.15:
            logger.warning(
                "Execution Filter | Layer 6 (Circuit Breaker) FAIL: Drawdown %.1f%%",
                current_drawdown * 100,
            )
            return False

        # Layer 5: Institutional Session Filter (08:00 - 21:00 GMT)
        hour = timestamp.hour
        if not (8 <= hour < 21):
            logger.debug(
                "Execution Filter | Layer 5 (Session) FAIL: Hour %d outside 08:00-21:00 GMT", hour
            )
            return False

        # Layers 1-4 require indicators from the latest bar
        if df_indicators.empty:
            logger.warning("Execution Filter | No indicator data available")
            return False

        latest = df_indicators.iloc[-1]

        # Layer 1: ATR Volatility Block (ATR(14) > 3x MA(100) of ATR)
        # Prevents trading in extremely low volatility or sudden erratic spikes if logic inverted
        # The memory says "ATR(14) > 3x MA(100) volatility block" which might mean block if too high?
        # Usually, institutional filters block if volatility is too low or too high.
        # Let's assume it blocks if ATR is > 3x its moving average (extreme volatility).
        atr = latest.get("atr_14", 0)
        atr_ma = latest.get("atr_14_ma_100", 0)
        if atr_ma > 0 and atr > 3 * atr_ma:
            logger.debug(
                "Execution Filter | Layer 1 (Volatility) FAIL: ATR %.2f > 3x MA %.2f", atr, atr_ma
            )
            return False

        # Layer 2: EMA Slope Confirmation
        # Check if EMA 50 is trending in the right direction
        ema_50 = latest.get("ema_50", 0)
        if len(df_indicators) > 1:
            prev_ema_50 = df_indicators.iloc[-2].get("ema_50", 0)
            slope = ema_50 - prev_ema_50
            if (signal_direction == 1 and slope <= 0) or (signal_direction == -1 and slope >= 0):
                logger.debug("Execution Filter | Layer 2 (EMA Slope) FAIL: Slope %.4f", slope)
                return False

        # Layer 3: EMA Sequence (EMA 20 > 50 > 200 for BUY)
        ema_20 = latest.get("ema_20", 0)
        ema_200 = latest.get("ema_200", 0)
        if signal_direction == 1 and not (ema_20 > ema_50 > ema_200):
            logger.debug("Execution Filter | Layer 3 (EMA Sequence) FAIL: BUY sequence mismatch")
            return False
        if signal_direction == -1 and not (ema_20 < ema_50 < ema_200):
            logger.debug("Execution Filter | Layer 3 (EMA Sequence) FAIL: SELL sequence mismatch")
            return False

        # Layer 4: RSI Momentum
        rsi = latest.get("rsi_14", 50)
        if signal_direction == 1 and rsi <= 50:
            logger.debug("Execution Filter | Layer 4 (RSI) FAIL: BUY RSI %.2f <= 50", rsi)
            return False
        if signal_direction == -1 and rsi >= 50:
            logger.debug("Execution Filter | Layer 4 (RSI) FAIL: SELL RSI %.2f >= 50", rsi)
            return False

        return True


__all__ = ["ExecutionFilter"]
