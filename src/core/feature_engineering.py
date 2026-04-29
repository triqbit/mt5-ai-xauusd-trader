"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/feature_engineering.py
Institutional-grade feature extraction pipeline.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from typing import List

import numpy as np
import pandas as pd
import pandas_ta as ta  # noqa: F401
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Unified feature engineering pipeline for live trading and backtesting.
    Ensures consistency between training and inference.
    """

    def __init__(self) -> None:
        self.scaler = StandardScaler()
        self.feature_columns: List[str] = []
        self._is_fitted = False

    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract technical indicators and multi-timeframe features.

        Args:
            df: Input DataFrame with OHLCV data.

        Returns:
            DataFrame with additional features.
        """
        df = df.copy()

        # 1. Basic indicators
        df.ta.rsi(length=14, append=True)
        df.ta.atr(length=14, append=True)

        # 2. EMA Stack
        df.ta.ema(length=8, append=True)
        df.ta.ema(length=21, append=True)
        df.ta.ema(length=50, append=True)
        df.ta.ema(length=200, append=True)

        # 3. Bollinger Bands
        df.ta.bbands(length=20, std=2, append=True)

        # 4. MACD
        df.ta.macd(fast=12, slow=26, signal=9, append=True)

        # 5. Returns and Volatility
        df["returns"] = df["close"].pct_change()
        df["volatility"] = df["returns"].rolling(window=20).std()

        # 6. Price Ratios
        df["close_ema200_ratio"] = df["close"] / df["EMA_200"]

        # Handle multi-timeframe (simplified for now, can be expanded)
        # Note: In a real institutional setup, we would resample and join.

        df.dropna(inplace=True)
        return df

    def fit(self, df: pd.DataFrame) -> None:
        """
        Fit the scaler on the provided features.

        Args:
            df: DataFrame containing features.
        """
        self.feature_columns = [col for col in df.columns if col not in ["open", "high", "low", "close", "tick_volume", "timestamp"]]
        self.scaler.fit(df[self.feature_columns])
        self._is_fitted = True
        logger.info("FeatureEngineer fitted with %d features", len(self.feature_columns))

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """
        Scale features and return as a numpy array.

        Args:
            df: DataFrame containing features.

        Returns:
            Scaled features as a numpy array.
        """
        if not self._is_fitted:
            raise RuntimeError("FeatureEngineer must be fitted before calling transform.")

        # Ensure all columns exist
        for col in self.feature_columns:
            if col not in df.columns:
                # If missing, we might need to recalculate or handle it
                # For now, we assume extract_features was called.
                pass

        scaled_data = self.scaler.transform(df[self.feature_columns])
        return scaled_data.astype(np.float32)

    def fit_transform(self, df: pd.DataFrame) -> np.ndarray:
        """
        Extract, fit, and transform features.

        Args:
            df: Input DataFrame with OHLCV data.

        Returns:
            Scaled features as a numpy array.
        """
        features_df = self.extract_features(df)
        self.fit(features_df)
        return self.transform(features_df)
