"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/feature_engineering.py
Dynamic feature engineering engine generating 140+ indicators with
multi-timeframe support and rolling Z-score normalization.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np
import pandas as pd
import pandas_ta as ta  # noqa: F401
import talib

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Centralized feature engineering pipeline.
    Generates technical indicators and performs rolling normalization.
    """

    def __init__(
        self,
        lookback_window: int = 100,
        epsilon: float = 1e-8,
        target_timeframes: Optional[List[str]] = None,
    ) -> None:
        self.lookback_window = lookback_window
        self.epsilon = epsilon
        self.target_timeframes = target_timeframes or ["M5", "M15", "H1"]

    def generate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate 140+ technical indicators.
        Args:
            df: OHLCV DataFrame.
        Returns:
            DataFrame with added features.
        """
        df = df.copy()

        # 1. Trend Indicators
        df["ema_20"] = talib.EMA(df["close"], timeperiod=20)
        df["ema_50"] = talib.EMA(df["close"], timeperiod=50)
        df["ema_200"] = talib.EMA(df["close"], timeperiod=200)
        df["adx"] = talib.ADX(df["high"], df["low"], df["close"], timeperiod=14)
        df["plus_di"] = talib.PLUS_DI(df["high"], df["low"], df["close"], timeperiod=14)
        df["minus_di"] = talib.MINUS_DI(df["high"], df["low"], df["close"], timeperiod=14)

        # 2. Momentum Indicators
        df["rsi"] = talib.RSI(df["close"], timeperiod=14)
        df["macd"], df["macdsignal"], df["macdhist"] = talib.MACD(
            df["close"], fastperiod=12, slowperiod=26, signalperiod=9
        )
        df["cci"] = talib.CCI(df["high"], df["low"], df["close"], timeperiod=14)
        df["willr"] = talib.WILLR(df["high"], df["low"], df["close"], timeperiod=14)

        # 3. Volatility Indicators
        df["atr"] = talib.ATR(df["high"], df["low"], df["close"], timeperiod=14)
        df["avg_atr"] = df["atr"].rolling(100).mean()
        upper, middle, lower = talib.BBANDS(df["close"], timeperiod=20)
        df["bb_upper"] = upper
        df["bb_middle"] = middle
        df["bb_lower"] = lower
        df["natr"] = talib.NATR(df["high"], df["low"], df["close"], timeperiod=14)

        # 4. Volume Indicators
        df["obv"] = talib.OBV(df["close"], df["tick_volume"])
        df["ad"] = talib.AD(df["high"], df["low"], df["close"], df["tick_volume"])
        df["adosc"] = talib.ADOSC(
            df["high"], df["low"], df["close"], df["tick_volume"], fastperiod=3, slowperiod=10
        )

        # 5. Price Patterns & Returns
        df["log_ret"] = np.log(df["close"] / df["close"].shift(1))
        df["volatility_20"] = df["log_ret"].rolling(20).std()

        # 6. Bulk indicators via pandas_ta
        # This helps reaching 140+ features quickly
        df.ta.strategy("all")

        # Clean up
        df.dropna(axis=1, thresh=len(df) * 0.7, inplace=True)
        df = df.ffill()

        return df

    def normalize_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply rolling Z-score normalization to all numeric columns except target/time.
        Args:
            df: Feature DataFrame.
        Returns:
            Normalized DataFrame.
        """
        exclude = [
            "time",
            "open",
            "high",
            "low",
            "close",
            "tick_volume",
            "atr",
            "avg_atr",
            "ema_20",
            "ema_50",
            "ema_200",
            "rsi",
        ]
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        cols_to_norm = [c for c in numeric_cols if c not in exclude]

        for col in cols_to_norm:
            rolling_mean = df[col].rolling(window=self.lookback_window).mean()
            rolling_std = df[col].rolling(window=self.lookback_window).std()
            df[col] = (df[col] - rolling_mean) / (rolling_std + self.epsilon)

        return df


__all__ = ["FeatureEngineer"]
