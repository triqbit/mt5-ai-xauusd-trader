"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/execution_filter.py
6-Layer Execution Filter Cascade to validate entry signals.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, time
from typing import Dict, Optional

import numpy as np
import pandas as pd

try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    import talib as ta
    PANDAS_TA_AVAILABLE = False

from src.trading.risk_manager import TradeSignal

logger = logging.getLogger(__name__)


@dataclass
class ExecutionDecision:
    """Outcome of the execution filter validation."""

    signal: TradeSignal
    approved: bool
    confidence_score: float
    blocked_by: Optional[str] = None


class ExecutionFilter:
    """
    Cascade validation for trading signals.
    Layers:
    1. ATR Volatility
    2. Trend Angle
    3. EMA Sequence
    4. Momentum
    5. Session/Time
    6. Drawdown Circuit Breaker
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        # ATR Configuration
        self.atr_period = self.config.get("atr_period", 14)
        self.min_atr = self.config.get("min_atr", 0.5)  # Gold specific default
        self.max_atr = self.config.get("max_atr", 10.0)

        # Trend Angle Configuration
        self.ma_period = self.config.get("ma_period", 50)
        self.threshold_slope = self.config.get("threshold_slope", 0.0001)

        # EMA Sequence Configuration
        self.ema_fast = self.config.get("ema_fast", 20)
        self.ema_mid = self.config.get("ema_mid", 50)
        self.ema_slow = self.config.get("ema_slow", 200)

        # Momentum Configuration
        self.rsi_period = self.config.get("rsi_period", 14)
        self.rsi_buy_min = self.config.get("rsi_buy_min", 50)
        self.rsi_sell_max = self.config.get("rsi_sell_max", 50)

        # Drawdown Configuration
        self.max_drawdown = self.config.get("max_drawdown", 0.15)

        # Session Configuration (UTC)
        self.allowed_sessions = self.config.get(
            "allowed_sessions",
            [
                {"start": time(8, 0), "end": time(21, 0)}  # London + NY overlap
            ],
        )

    def validate(
        self, signal: TradeSignal, df: pd.DataFrame, account_stats: Dict
    ) -> ExecutionDecision:
        """Run all filters in cascade."""
        # 1. ATR Volatility
        if not self._check_atr_volatility(df):
            return self._reject(signal, "ATR Volatility")

        # 2. Trend Angle
        if not self._check_trend_angle(df, signal.direction):
            return self._reject(signal, "Trend Angle")

        # 3. EMA Sequence
        if not self._check_ema_sequence(df, signal.direction):
            return self._reject(signal, "EMA Sequence")

        # 4. Momentum
        if not self._check_momentum(df, signal.direction):
            return self._reject(signal, "Momentum")

        # 5. Session Filter
        if not self._check_session_filter(signal.timestamp):
            return self._reject(signal, "Session Filter")

        # 6. Drawdown Breaker
        if not self._check_drawdown_breaker(account_stats):
            return self._reject(signal, "Drawdown Breaker")

        logger.info("Signal APPROVED: %s %d", signal.symbol, signal.direction)
        return ExecutionDecision(
            signal=signal, approved=True, confidence_score=signal.confidence
        )

    def _reject(self, signal: TradeSignal, reason: str) -> ExecutionDecision:
        logger.warning("Signal BLOCKED by %s: %s %d", reason, signal.symbol, signal.direction)
        return ExecutionDecision(
            signal=signal, approved=False, confidence_score=0.0, blocked_by=reason
        )

    def _check_atr_volatility(self, df: pd.DataFrame) -> bool:
        if PANDAS_TA_AVAILABLE:
            atr = df.ta.atr(length=self.atr_period)
        else:
            atr = pd.Series(
                ta.ATR(df["high"], df["low"], df["close"], timeperiod=self.atr_period),
                index=df.index,
            )

        if atr is None or len(atr) == 0 or np.isnan(atr.iloc[-1]):
            return False
        current_atr = atr.iloc[-1]
        return bool(self.min_atr <= current_atr <= self.max_atr)

    def _check_trend_angle(self, df: pd.DataFrame, direction: int) -> bool:
        if PANDAS_TA_AVAILABLE:
            ma = df.ta.sma(length=self.ma_period)
        else:
            ma = pd.Series(
                ta.SMA(df["close"], timeperiod=self.ma_period), index=df.index
            )

        if ma is None or len(ma) < 2 or np.isnan(ma.iloc[-1]) or np.isnan(ma.iloc[-2]):
            return False
        # Calculate slope: (current - prev) / prev
        slope = (ma.iloc[-1] - ma.iloc[-2]) / ma.iloc[-2]
        if direction == 1:  # Buy
            return bool(slope > self.threshold_slope)
        if direction == -1:  # Sell
            return bool(slope < -self.threshold_slope)
        return False

    def _check_ema_sequence(self, df: pd.DataFrame, direction: int) -> bool:
        if PANDAS_TA_AVAILABLE:
            ema_f = df.ta.ema(length=self.ema_fast)
            ema_m = df.ta.ema(length=self.ema_mid)
            ema_s = df.ta.ema(length=self.ema_slow)
        else:
            ema_f = pd.Series(
                ta.EMA(df["close"], timeperiod=self.ema_fast), index=df.index
            )
            ema_m = pd.Series(
                ta.EMA(df["close"], timeperiod=self.ema_mid), index=df.index
            )
            ema_s = pd.Series(
                ta.EMA(df["close"], timeperiod=self.ema_slow), index=df.index
            )

        if ema_f is None or ema_m is None or ema_s is None:
            return False
        if len(ema_f) == 0 or len(ema_m) == 0 or len(ema_s) == 0:
            return False
        if (
            np.isnan(ema_f.iloc[-1])
            or np.isnan(ema_m.iloc[-1])
            or np.isnan(ema_s.iloc[-1])
        ):
            return False

        f, m, s = ema_f.iloc[-1], ema_m.iloc[-1], ema_s.iloc[-1]
        if direction == 1:  # Buy: Fast > Mid > Slow
            return bool(f > m > s)
        if direction == -1:  # Sell: Fast < Mid < Slow
            return bool(f < m < s)
        return False

    def _check_momentum(self, df: pd.DataFrame, direction: int) -> bool:
        if PANDAS_TA_AVAILABLE:
            rsi = df.ta.rsi(length=self.rsi_period)
        else:
            rsi = pd.Series(
                ta.RSI(df["close"], timeperiod=self.rsi_period), index=df.index
            )

        if rsi is None or len(rsi) == 0 or np.isnan(rsi.iloc[-1]):
            return False
        curr_rsi = rsi.iloc[-1]
        if direction == 1:  # Buy
            return bool(curr_rsi > self.rsi_buy_min)
        if direction == -1:  # Sell
            return bool(curr_rsi < self.rsi_sell_max)
        return False

    def _check_session_filter(self, timestamp: datetime) -> bool:
        current_time = timestamp.time()
        for session in self.allowed_sessions:
            if session["start"] <= current_time <= session["end"]:
                return True
        return False

    def _check_drawdown_breaker(self, account_stats: Dict) -> bool:
        drawdown = account_stats.get("drawdown", 0.0)
        return drawdown < self.max_drawdown
