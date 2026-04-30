"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/execution_filter.py
6-layer execution filter for trade signal validation.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
import pandas_ta as ta

from src.core.config import TradingConfig
from src.trading.risk_manager import TradeSignal

logger = logging.getLogger(__name__)

@dataclass
class ExecutionDecision:
    """Detailed result of the execution filter validation."""
    signal: TradeSignal
    is_approved: bool
    confidence_score: float
    blocked_by: Optional[str] = None

class ExecutionFilter:
    """
    Institutional-grade 6-layer execution filter.
    Validates signals against volatility, trend, momentum, time, and risk constraints.
    """
    def __init__(self, config: TradingConfig) -> None:
        self.cfg = config

    def validate(
        self,
        signal: TradeSignal,
        df: pd.DataFrame,
        account_stats: dict
    ) -> ExecutionDecision:
        """
        Run the full 6-layer validation cascade.
        """
        # Layer 1: ATR Volatility Threshold
        if not self._check_atr_volatility(df):
            return ExecutionDecision(signal, False, signal.confidence, "ATR_VOLATILITY")

        # Layer 2: Trend Angle Confirmation
        if not self._check_trend_angle(df, signal.direction):
            return ExecutionDecision(signal, False, signal.confidence, "TREND_ANGLE")

        # Layer 3: EMA Sequence Check
        if not self._check_ema_sequence(df, signal.direction):
            return ExecutionDecision(signal, False, signal.confidence, "EMA_SEQUENCE")

        # Layer 4: Momentum Filter
        if not self._check_momentum(df, signal.direction):
            return ExecutionDecision(signal, False, signal.confidence, "MOMENTUM")

        # Layer 5: Session/Time Filter
        if not self._check_session_time():
            return ExecutionDecision(signal, False, signal.confidence, "SESSION_TIME")

        # Layer 6: Drawdown Circuit Breaker
        if not self._check_drawdown(account_stats):
            return ExecutionDecision(signal, False, signal.confidence, "DRAWDOWN")

        return ExecutionDecision(
            signal=signal,
            is_approved=True,
            confidence_score=signal.confidence,
            blocked_by=None
        )

    def _check_atr_volatility(self, df: pd.DataFrame) -> bool:
        """
        Layer 1: ATR Volatility Threshold.
        Blocks if current 14-period ATR > 3x the 30-period average ATR.
        """
        if len(df) < 15:
            return True

        atr = ta.atr(df["high"], df["low"], df["close"], length=14)
        if atr is None or len(atr) < 30:
            # Not enough data for 30-period average, but we can still check against available
            if atr is not None and not atr.empty:
                current_atr = atr.iloc[-1]
                avg_atr = atr.mean()
                if current_atr > 3.0 * avg_atr:
                    return False
            return True

        current_atr = atr.iloc[-1]
        avg_atr = atr.rolling(window=30).mean().iloc[-1]

        if np.isnan(avg_atr) or avg_atr == 0:
            return True

        if current_atr > 3.0 * avg_atr:
            logger.warning("ATR Volatility too high: %.4f (limit: %.4f)", current_atr, 3.0 * avg_atr)
            return False
        return True

    def _check_trend_angle(self, df: pd.DataFrame, direction: int) -> bool:
        """
        Layer 2: Trend Angle Confirmation.
        Calculates the slope of the 20-period EMA over the last 3 bars.
        Blocks if the slope is not in the direction of the trade.
        """
        if len(df) < 20:
            return True

        ema20 = ta.ema(df["close"], length=20)
        if ema20 is None or len(ema20) < 3:
            return True

        # Last 3 points of EMA20
        y = ema20.tail(3).values
        x = np.arange(len(y))

        # Calculate slope via linear regression
        slope = np.polyfit(x, y, 1)[0]

        # Normalize slope (optional, but good for relative strength)
        # angle = np.arctan(slope) * (180 / np.pi)

        if direction == 1 and slope <= 0:
            logger.debug("Trend Angle rejection (BUY): slope %.4f <= 0", slope)
            return False
        if direction == -1 and slope >= 0:
            logger.debug("Trend Angle rejection (SELL): slope %.4f >= 0", slope)
            return False

        return True

    def _check_ema_sequence(self, df: pd.DataFrame, direction: int) -> bool:
        """
        Layer 3: EMA Sequence Check.
        Checks if EMA20 > EMA50 > EMA200 for BUY.
        Checks if EMA20 < EMA50 < EMA200 for SELL.
        """
        if len(df) < 200:
            return True

        ema20 = ta.ema(df["close"], length=20)
        ema50 = ta.ema(df["close"], length=50)
        ema200 = ta.ema(df["close"], length=200)

        if ema20 is None or ema50 is None or ema200 is None:
            return True

        e20, e50, e200 = ema20.iloc[-1], ema50.iloc[-1], ema200.iloc[-1]

        if direction == 1 and not (e20 > e50 > e200):
            logger.debug("EMA Sequence rejection (BUY): %s, %s, %s", e20, e50, e200)
            return False
        if direction == -1 and not (e20 < e50 < e200):
            logger.debug("EMA Sequence rejection (SELL): %s, %s, %s", e20, e50, e200)
            return False

        return True

    def _check_session_time(self) -> bool:
        """
        Layer 5: Session/Time Filter.
        Blocks trading during weekend and low liquidity periods.
        Approved: Sunday 17:00 to Friday 16:00 GMT.
        """
        now_utc = datetime.now(timezone.utc)
        weekday = now_utc.weekday()  # 0=Monday, 6=Sunday
        hour = now_utc.hour

        # Friday 16:00 to Sunday 17:00 is CLOSED
        if weekday == 4 and hour >= 16:  # Friday
            return False
        if weekday == 5:  # Saturday
            return False
        return not (weekday == 6 and hour < 17)

    def _check_drawdown(self, account_stats: dict) -> bool:
        """
        Layer 6: Drawdown Circuit Breaker.
        Blocks trading if current drawdown exceeds 15%.
        Expects 'balance' and 'peak_equity' in account_stats.
        """
        balance = account_stats.get("balance", 0)
        peak_equity = account_stats.get("peak_equity", 0)

        if peak_equity <= 0:
            return True

        drawdown = (peak_equity - balance) / peak_equity
        if drawdown >= 0.15:
            logger.critical("Circuit Breaker: Drawdown %.2f%% exceeds 15%% limit", drawdown * 100)
            return False
        return True

    def _check_momentum(self, df: pd.DataFrame, direction: int) -> bool:
        """
        Layer 4: Momentum Filter.
        Uses RSI to ensure trade is in the direction of momentum but not overextended.
        BUY: RSI > 50 and RSI < 75
        SELL: RSI < 50 and RSI > 25
        """
        if len(df) < 14:
            return True

        rsi = ta.rsi(df["close"], length=14)
        if rsi is None or rsi.empty:
            return True

        current_rsi = rsi.iloc[-1]

        if direction == 1 and (current_rsi <= 50 or current_rsi >= 75):
            logger.debug("Momentum rejection (BUY): RSI %.2f", current_rsi)
            return False
        if direction == -1 and (current_rsi >= 50 or current_rsi <= 25):
            logger.debug("Momentum rejection (SELL): RSI %.2f", current_rsi)
            return False

        return True
