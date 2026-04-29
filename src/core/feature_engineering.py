"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/feature_engineering.py
Compute 140+ institutional-grade features from raw OHLCV data using TA-Lib.
Includes multi-timeframe analysis, candle patterns, and volume profiling.
Author : triqbit
License: MIT
"""

from __future__ import annotations

from typing import List

import pandas as pd
import talib
from sklearn.preprocessing import StandardScaler


class FeatureEngineer:
    """
    State-of-the-art feature engineering pipeline for XAUUSD trading.

    This class transforms raw OHLCV data into a rich feature set (140+ features)
    suitable for deep learning and reinforcement learning models.
    """

    def __init__(self, primary_tf: str = "M5"):
        """
        Initialize the feature engineer.

        Args:
            primary_tf: The primary timeframe of the input data (e.g., 'M1', 'M5').
        """
        self.primary_tf = primary_tf
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.feature_columns: List[str] = []

        # Define candle patterns available in TA-Lib
        self.candle_names = talib.get_function_groups()['Pattern Recognition']

    def compute_base_indicators(self, df: pd.DataFrame, prefix: str = "") -> pd.DataFrame:
        """
        Compute core technical indicators (RSI, MACD, ATR, BBands, EMAs).

        Args:
            df: Input DataFrame with 'open', 'high', 'low', 'close', 'volume'.

        Returns:
            DataFrame with added indicators.
        """
        df = df.copy()
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values

        # RSI
        df[f'{prefix}RSI'] = talib.RSI(close, timeperiod=14)

        # MACD
        macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        df[f'{prefix}MACD'] = macd
        df[f'{prefix}MACD_signal'] = macdsignal
        df[f'{prefix}MACD_hist'] = macdhist

        # ATR
        df[f'{prefix}ATR'] = talib.ATR(high, low, close, timeperiod=14)

        # Bollinger Bands
        upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        df[f'{prefix}BB_upper'] = upper
        df[f'{prefix}BB_middle'] = middle
        df[f'{prefix}BB_lower'] = lower
        df[f'{prefix}BB_width'] = (upper - lower) / middle

        # EMA stacks
        for period in [8, 21, 50, 200]:
            df[f'{prefix}EMA_{period}'] = talib.EMA(close, timeperiod=period)
            # Distance from EMA as a feature
            df[f'{prefix}DIST_EMA_{period}'] = (close - df[f'{prefix}EMA_{period}']) / df[f'{prefix}EMA_{period}']

        return df

    def _add_mtf_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Resample and compute indicators for multiple timeframes (M1, M5, M15, H1, H4, D1).

        Args:
            df: Input DataFrame with DatetimeIndex and OHLCV columns.

        Returns:
            DataFrame with merged MTF features.
        """
        # Ensure 'min' is used instead of 'T' for pandas >= 2.0
        timeframes = {
            "M1": "1min",
            "M5": "5min",
            "M15": "15min",
            "H1": "1h",
            "H4": "4h",
            "D1": "1d"
        }

        original_df = df.copy()

        for tf_name, tf_freq in timeframes.items():
            if tf_name == self.primary_tf:
                continue

            # Resample
            resampled = df.resample(tf_freq).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()

            # Compute indicators on resampled data
            resampled = self.compute_base_indicators(resampled, prefix=f"{tf_name}_")

            # Drop OHLCV from resampled to avoid collisions
            resampled = resampled.drop(columns=['open', 'high', 'low', 'close', 'volume'])

            # Shift resampled data to prevent look-ahead bias
            # Resampled bars are labeled by their start time, so we must shift them
            # to ensure we only use the data once the bar is actually closed.
            resampled = resampled.shift(1)

            # Merge back to original data using forward fill
            original_df = pd.merge_asof(
                original_df.sort_index(),
                resampled.sort_index(),
                left_index=True,
                right_index=True,
                direction='backward'
            )

        return original_df

    def _add_candle_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Recognize 60+ TA-Lib candle patterns.

        Args:
            df: Input DataFrame.

        Returns:
            DataFrame with candle pattern features.
        """
        op = df['open'].values
        hi = df['high'].values
        lo = df['low'].values
        cl = df['close'].values

        for pattern in self.candle_names:
            # Pattern recognition functions return -100, 0, or 100
            # We divide by 100 to get -1, 0, 1
            df[pattern] = getattr(talib, pattern)(op, hi, lo, cl) / 100.0

        return df

    def _add_volume_profile(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add volume-based indicators (OBV, AD, ADOSC).

        Args:
            df: Input DataFrame.

        Returns:
            DataFrame with volume features.
        """
        cl = df['close'].values
        hi = df['high'].values
        lo = df['low'].values
        vo = df['volume'].values

        df['OBV'] = talib.OBV(cl, vo)
        df['AD'] = talib.AD(hi, lo, cl, vo)
        df['ADOSC'] = talib.ADOSC(hi, lo, cl, vo, fastperiod=3, slowperiod=10)

        return df

    def extract_features(self, df: pd.DataFrame, fit_scaler: bool = False) -> pd.DataFrame:
        """
        Full feature extraction pipeline.

        Args:
            df: Input OHLCV DataFrame.
            fit_scaler: Whether to fit the internal scaler.

        Returns:
            Processed and normalized feature matrix.
        """
        # 1. Base indicators
        df = self.compute_base_indicators(df)

        # 2. Multi-timeframe features
        df = self._add_mtf_features(df)

        # 3. Candle patterns
        df = self._add_candle_patterns(df)

        # 4. Volume profile
        df = self._add_volume_profile(df)

        # 5. Handle NaNs from indicators warmup
        # Drop columns that are all NaN (might happen with some MTF features if data is short)
        df = df.dropna(axis=1, how='all')
        # Drop rows with NaNs (warmup period)
        df = df.dropna()

        # 6. Drop OHLCV before normalization
        features_df = df.drop(columns=['open', 'high', 'low', 'close', 'volume'])

        # 7. Normalization
        if fit_scaler:
            self.scaler.fit(features_df)
            self.feature_columns = features_df.columns.tolist()
            self.is_fitted = True

        if self.is_fitted:
            # Ensure we only use columns present during fitting
            missing_cols = set(self.feature_columns) - set(features_df.columns)
            if missing_cols:
                # If some features are missing in the current data, we can't normalize properly
                # For now, let's just use what we have if it matches, or handle appropriately
                # Ideally, we should pad with zeros or handle as a failure
                for col in missing_cols:
                    features_df[col] = 0.0

            # Only use and reorder columns to match fit order
            features_df = features_df[self.feature_columns]

            normalized_data = self.scaler.transform(features_df)
            normalized_df = pd.DataFrame(
                normalized_data,
                index=features_df.index,
                columns=self.feature_columns
            )
            return normalized_df

        return features_df
