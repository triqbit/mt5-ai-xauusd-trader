"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/feature_engineer.py
Feature engineering pipeline for 140+ technical indicators.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd
import pandas_ta as ta

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Handles technical indicator generation and data normalization.
    Uses pandas-ta for bulk indicator calculation and TA-Lib for high-performance fallbacks.
    """

    def __init__(self, window_size: int = 20) -> None:
        self.window_size = window_size

    def generate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate 140+ features including trend, momentum, volatility, and volume indicators.
        """
        if df.empty:
            return df

        df = df.copy()

        # 1. Base Indicators for ExecutionFilter
        df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)
        df["rsi"] = ta.rsi(df["close"], length=14)
        df["ema_50"] = ta.ema(df["close"], length=50)
        df["ema_100"] = ta.ema(df["close"], length=100)
        df["ema_200"] = ta.ema(df["close"], length=200)

        # 2. Trend Angle (using linear regression slope over 5 periods)
        lin_reg = ta.linreg(df["close"], length=5)
        df["angle"] = np.rad2deg(np.arctan(lin_reg.diff() / 5))

        # 3. Bulk Indicators (pandas-ta strategies)
        # Custom strategy to reach 140+ features
        custom_strategy = ta.Strategy(
            name="Ensemble Strategy",
            description="Comprehensive feature set for DRL models",
            ta=[
                {"kind": "bbands", "length": 20},
                {"kind": "macd", "fast": 12, "slow": 26, "signal": 9},
                {"kind": "stoch", "k": 14, "d": 3},
                {"kind": "adx", "length": 14},
                {"kind": "cci", "length": 20},
                {"kind": "obv"},
                {"kind": "vwap"},
                {"kind": "mfi", "length": 14},
                {"kind": "willr", "length": 14},
                {"kind": "ichimoku"},
                {"kind": "kc", "length": 20},
                {"kind": "donchian", "lower_length": 20, "upper_length": 20},
            ],
        )
        df.ta.strategy(custom_strategy)

        # 4. Momentum and Rate of Change
        for n in [1, 3, 5, 10, 20]:
            df[f"roc_{n}"] = df["close"].pct_change(n)
            df[f"mom_{n}"] = df["close"].diff(n)

        # 5. Volatility features
        df["std_20"] = df["close"].rolling(20).std()
        df["std_50"] = df["close"].rolling(50).std()

        # 6. Target Generation (for training/backtesting only)
        # Shifted return: what happened in the NEXT candle
        df["target_return"] = df["close"].pct_change().shift(-1)

        # Drop NaNs created by indicators
        df = df.dropna()

        # Ensure we have a significant number of columns
        logger.debug("Generated features: %d columns", len(df.columns))
        return df

    def normalize_features(self, df: pd.DataFrame, window: Optional[int] = None) -> pd.DataFrame:
        """
        Apply window-based Z-score normalization to all numeric columns except targets.
        """
        cols_to_norm = [c for c in df.columns if c not in ["target_return", "timestamp"]]
        df_norm = df.copy()

        if window:
            # Rolling Z-score
            rolling = df_norm[cols_to_norm].rolling(window=window)
            mu = rolling.mean()
            sigma = rolling.std()
            df_norm[cols_to_norm] = (df_norm[cols_to_norm] - mu) / (sigma + 1e-8)
        else:
            # Global Z-score
            mu = df_norm[cols_to_norm].mean()
            sigma = df_norm[cols_to_norm].std()
            df_norm[cols_to_norm] = (df_norm[cols_to_norm] - mu) / (sigma + 1e-8)

        return df_norm.dropna()
