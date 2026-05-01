"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/execution_filter.py
8-layer execution filter implementing cascading technical validation.
Layers: ATR, Trend Angle, EMA Sequence, Momentum, Session, Spread, ADX, Drawdown.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional, TYPE_CHECKING

import numpy as np
import pandas as pd
from scipy.stats import linregress

if TYPE_CHECKING:
    from src.trading.risk_manager import TradeSignal

logger = logging.getLogger(__name__)


@dataclass
class ExecutionDecision:
    """Result of the execution filter validation."""
    signal: TradeSignal
    is_approved: bool
    confidence_score: float
    blocked_by: Optional[str] = None


class ExecutionFilter:
    """
    Cascading execution filter for vetting trading signals.
    Implements 8 layers of technical and environmental validation.
    """

    def __init__(self):
        # Configuration for filter layers
        self.atr_multiplier = 3.0
        self.drawdown_limit = 0.15
        self.min_rsi_buy = 50.0
        self.max_rsi_buy = 75.0
        self.min_rsi_sell = 25.0
        self.max_rsi_sell = 50.0
        self.min_adx = 25.0

    def validate(
        self,
        signal: TradeSignal,
        market_data: pd.DataFrame,
        current_drawdown: float,
        current_spread: float = 0.0
    ) -> ExecutionDecision:
        """
        Run all filter layers in a cascading sequence.
        Returns ExecutionDecision.
        """
        # Layer 1: Session/Time Filter
        if not self._check_session_time():
            return ExecutionDecision(signal, False, 0.0, "Session Filter")

        # Layer 2: Drawdown Circuit Breaker
        if current_drawdown > self.drawdown_limit:
            return ExecutionDecision(signal, False, 0.0, "Drawdown Circuit Breaker")

        # Layer 3: ATR Volatility
        if not self._check_atr_volatility(market_data):
            return ExecutionDecision(signal, False, 0.0, "ATR Volatility")

        # Layer 4: EMA Sequence
        if not self._check_ema_sequence(market_data, signal.direction):
            return ExecutionDecision(signal, False, 0.0, "EMA Sequence")

        # Layer 5: Trend Angle
        if not self._check_trend_angle(market_data, signal.direction):
            return ExecutionDecision(signal, False, 0.0, "Trend Angle")

        # Layer 6: Momentum (RSI)
        if not self._check_momentum(market_data, signal.direction):
            return ExecutionDecision(signal, False, 0.0, "Momentum Filter")

        # Layer 7: Spread Check (If provided)
        if current_spread > 0 and not self._check_spread(market_data, current_spread):
            return ExecutionDecision(signal, False, 0.0, "Spread Check")

        # Layer 8: ADX Trend Strength
        if not self._check_adx(market_data):
            return ExecutionDecision(signal, False, 0.0, "ADX Trend Strength")

        return ExecutionDecision(signal, True, signal.confidence, None)

    # -- Filter Layer Implementations ---------------------------------------

    def _check_session_time(self) -> bool:
        """
        XAUUSD institutional hours: Sunday 17:00 to Friday 16:00 GMT.
        """
        now = datetime.utcnow()
        weekday = now.weekday()  # 0=Monday, 6=Sunday
        current_time = now.time()

        if weekday == 5:  # Saturday
            return False
        if weekday == 6:  # Sunday
            return current_time >= time(17, 0)
        if weekday == 4:  # Friday
            return current_time <= time(16, 0)

        return True

    def _check_atr_volatility(self, df: pd.DataFrame) -> bool:
        """
        Rejects if ATR(14) > 3 * SMA(ATR(14), 30).
        """
        if len(df) < 44:  # 14 + 30
            return True

        high = df['high']
        low = df['low']
        close_prev = df['close'].shift(1)

        tr = pd.concat([
            high - low,
            (high - close_prev).abs(),
            (low - close_prev).abs()
        ], axis=1).max(axis=1)

        atr = tr.rolling(window=14).mean()
        atr_sma = atr.rolling(window=30).mean()

        current_atr = atr.iloc[-1]
        avg_atr = atr_sma.iloc[-1]

        if pd.isna(current_atr) or pd.isna(avg_atr):
            return True

        return current_atr <= (avg_atr * self.atr_multiplier)

    def _check_ema_sequence(self, df: pd.DataFrame, direction: int) -> bool:
        """
        BUY: EMA20 > EMA50 > EMA200
        SELL: EMA20 < EMA50 < EMA200
        """
        if len(df) < 200:
            return True

        ema20 = df['close'].ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = df['close'].ewm(span=50, adjust=False).mean().iloc[-1]
        ema200 = df['close'].ewm(span=200, adjust=False).mean().iloc[-1]

        if direction == 1:  # BUY
            return ema20 > ema50 > ema200
        elif direction == -1:  # SELL
            return ema20 < ema50 < ema200

        return False

    def _check_trend_angle(self, df: pd.DataFrame, direction: int) -> bool:
        """
        Linear regression slope of EMA20 over last 10 periods.
        """
        if len(df) < 30:
            return True

        ema20 = df['close'].ewm(span=20, adjust=False).mean()
        recent_ema = ema20.iloc[-10:].values
        x = np.arange(len(recent_ema))

        slope, _, _, _, _ = linregress(x, recent_ema)

        if direction == 1:
            return slope > 0
        elif direction == -1:
            return slope < 0

        return False

    def _check_momentum(self, df: pd.DataFrame, direction: int) -> bool:
        """
        BUY: RSI between 50 and 75
        SELL: RSI between 25 and 50
        """
        if len(df) < 15:
            return True

        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()

        # Handle division by zero
        loss_safe = loss.replace(0, 1e-9)
        rs = gain / loss_safe
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]

        if pd.isna(current_rsi):
            return True

        if direction == 1:
            return self.min_rsi_buy <= current_rsi <= self.max_rsi_buy
        elif direction == -1:
            return self.min_rsi_sell <= current_rsi <= self.max_rsi_sell

        return False

    def _check_spread(self, df: pd.DataFrame, current_spread: float) -> bool:
        """
        Blocks if spread > 3x average spread (if average spread info available).
        For now, just a sanity check if spread > 50 points (5.0 pips for Gold).
        """
        return current_spread <= 50.0

    def _check_adx(self, df: pd.DataFrame) -> bool:
        """
        Trend strength: ADX(14) > 25.
        """
        if len(df) < 28:
            return True

        # Simplified ADX implementation
        high = df['high']
        low = df['low']
        close_prev = df['close'].shift(1)

        tr = pd.concat([
            high - low,
            (high - close_prev).abs(),
            (low - close_prev).abs()
        ], axis=1).max(axis=1)

        up_move = high - high.shift(1)
        down_move = low.shift(1) - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        tr_smooth = tr.rolling(window=14).mean()
        plus_di = 100 * (pd.Series(plus_dm).rolling(window=14).mean() / tr_smooth)
        minus_di = 100 * (pd.Series(minus_dm).rolling(window=14).mean() / tr_smooth)

        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
        adx = dx.rolling(window=14).mean()

        current_adx = adx.iloc[-1]
        if pd.isna(current_adx):
            return True

        return current_adx >= self.min_adx
