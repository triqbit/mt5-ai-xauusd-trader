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

    def _calculate_atr(self, df: pd.DataFrame, length: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(window=length).mean()

    def _calculate_ema(self, series: pd.Series, length: int) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return series.ewm(span=length, adjust=False).mean()

    def _calculate_rsi(self, series: pd.Series, length: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.ewm(com=length - 1, adjust=False).mean()
        avg_loss = loss.ewm(com=length - 1, adjust=False).mean()

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _check_atr_volatility(self, df: pd.DataFrame) -> bool:
        """
        Layer 1: ATR Volatility Threshold.
        Blocks if current 14-period ATR > 3x the 30-period average ATR.
        """
        if len(df) < 15:
            return True

        atr = self._calculate_atr(df, length=14)
        if len(atr) < 30:
            current_atr = atr.iloc[-1]
            avg_atr = atr.mean()
            if not np.isnan(avg_atr) and avg_atr != 0:
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

        ema20 = self._calculate_ema(df["close"], length=20)
        if len(ema20) < 3:
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

        ema20 = self._calculate_ema(df["close"], length=20)
        ema50 = self._calculate_ema(df["close"], length=50)
        ema200 = self._calculate_ema(df["close"], length=200)

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
        if len(df) < 15:  # Need at least length + 1
            return True

        rsi = self._calculate_rsi(df["close"], length=14)
        if rsi.empty or np.isnan(rsi.iloc[-1]):
            return True

        current_rsi = rsi.iloc[-1]

        if direction == 1 and (current_rsi <= 50 or current_rsi >= 75):
            logger.debug("Momentum rejection (BUY): RSI %.2f", current_rsi)
            return False
        if direction == -1 and (current_rsi >= 50 or current_rsi <= 25):
            logger.debug("Momentum rejection (SELL): RSI %.2f", current_rsi)
            return False

        return True
