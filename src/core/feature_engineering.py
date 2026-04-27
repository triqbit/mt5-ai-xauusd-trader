"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/feature_engineering.py
Feature engineering module for computing 140+ technical indicators and patterns.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import talib

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Computes a comprehensive set of 140+ features from OHLCV data.

    Includes multi-timeframe indicators, candle patterns, and volume metrics.
    Output is normalized for model inference.
    """

    def __init__(self, base_timeframe: str = "M1"):
        """
        Initialize the FeatureEngineer.

        Args:
            base_timeframe: The timeframe of the input DataFrame (default: "M1").
        """
        self.base_timeframe = base_timeframe
        self.timeframes = ["M1", "M5", "M15", "H1", "H4", "D1"]
        self.ema_periods = [8, 21, 50, 200]

    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute the full feature set from OHLCV data.

        Args:
            df: Input DataFrame with columns ['open', 'high', 'low', 'close', 'tick_volume'].
                Must have a DatetimeIndex.

        Returns:
            DataFrame with normalized features.
        """
        if df.empty:
            return pd.DataFrame()

        # Ensure index is datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        # 1. Base technical indicators
        features_df = self._compute_indicators(df, label=self.base_timeframe)

        # 2. Multi-timeframe features
        for tf in self.timeframes:
            if tf == self.base_timeframe:
                continue

            resampled_df = self._resample_data(df, tf)
            tf_indicators = self._compute_indicators(resampled_df, label=tf)

            # Shift by 1 to avoid look-ahead bias (only use completed bars)
            tf_indicators = tf_indicators.shift(1)

            # Reindex and forward fill to match original index
            tf_indicators = tf_indicators.reindex(df.index).ffill()
            features_df = pd.concat([features_df, tf_indicators], axis=1)

        # 3. Candle pattern recognition (computed on base timeframe)
        candle_patterns = self._compute_candle_patterns(df)
        features_df = pd.concat([features_df, candle_patterns], axis=1)

        # 4. Volume profile / relative volume
        features_df = self._add_volume_features(features_df, df)

        # 5. Normalization
        normalized_df = self._normalize_features(features_df)

        return normalized_df

    def _resample_data(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Resample OHLCV data to a different timeframe."""
        mapping = {
            "M1": "1min",
            "M5": "5min",
            "M15": "15min",
            "H1": "1h",
            "H4": "4h",
            "D1": "1d"
        }
        freq = mapping.get(timeframe, "1min")

        resampled = df.resample(freq).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'tick_volume': 'sum'
        }).dropna()

        return resampled

    def _compute_indicators(self, df: pd.DataFrame, label: str) -> pd.DataFrame:
        """Compute core technical indicators for a given timeframe."""
        close = df['close'].values.astype(float)
        high = df['high'].values.astype(float)
        low = df['low'].values.astype(float)

        indicators = pd.DataFrame(index=df.index)

        # RSI
        indicators[f'{label}_RSI'] = talib.RSI(close, timeperiod=14)

        # MACD
        macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        indicators[f'{label}_MACD'] = macd
        indicators[f'{label}_MACD_Signal'] = macdsignal
        indicators[f'{label}_MACD_Hist'] = macdhist

        # ATR
        indicators[f'{label}_ATR'] = talib.ATR(high, low, close, timeperiod=14)

        # Bollinger Bands
        upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        indicators[f'{label}_BB_Upper'] = upper
        indicators[f'{label}_BB_Middle'] = middle
        indicators[f'{label}_BB_Lower'] = lower
        indicators[f'{label}_BB_Width'] = (upper - lower) / middle

        # EMA Stacks
        for period in self.ema_periods:
            indicators[f'{label}_EMA_{period}'] = talib.EMA(close, timeperiod=period)
            # Distance from price
            indicators[f'{label}_EMA_{period}_Dist'] = (close - indicators[f'{label}_EMA_{period}']) / close

        # Momentum Indicators
        indicators[f'{label}_ADX'] = talib.ADX(high, low, close, timeperiod=14)
        indicators[f'{label}_CCI'] = talib.CCI(high, low, close, timeperiod=14)
        indicators[f'{label}_MOM'] = talib.MOM(close, timeperiod=10)
        indicators[f'{label}_ROC'] = talib.ROC(close, timeperiod=10)

        # Volatility
        indicators[f'{label}_NATR'] = talib.NATR(high, low, close, timeperiod=14)

        return indicators

    def _compute_candle_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Identify all TA-Lib candlestick patterns."""
        open_p = df['open'].values.astype(float)
        high = df['high'].values.astype(float)
        low = df['low'].values.astype(float)
        close = df['close'].values.astype(float)

        patterns = pd.DataFrame(index=df.index)

        # Get all pattern functions from TA-Lib
        pattern_functions = talib.get_function_groups()['Pattern Recognition']

        for func_name in pattern_functions:
            func = getattr(talib, func_name)
            patterns[f'Pattern_{func_name}'] = func(open_p, high, low, close)

        return patterns

    def _add_volume_features(self, features_df: pd.DataFrame, raw_df: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based indicators."""
        close = raw_df['close'].values.astype(float)
        high = raw_df['high'].values.astype(float)
        low = raw_df['low'].values.astype(float)
        volume = raw_df['tick_volume'].values.astype(float)

        # On Balance Volume
        features_df['OBV'] = talib.OBV(close, volume)

        # Chaikin A/D Line
        features_df['AD'] = talib.AD(high, low, close, volume)

        # Relative Volume (ratio to 20-period average)
        avg_volume = raw_df['tick_volume'].rolling(window=20).mean()
        features_df['Rel_Volume'] = raw_df['tick_volume'] / (avg_volume + 1e-8)

        return features_df

    def _normalize_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply Z-score normalization and handle edge cases."""
        # Drop columns with all NaNs
        df = df.dropna(axis=1, how='all')

        # Drop rows with NaNs caused by indicators warmup
        df = df.dropna()

        if df.empty:
            logger.warning("Feature matrix is empty after dropping NaNs. Check input data length.")
            return df

        # Handle infinities
        df = df.replace([np.inf, -np.inf], 0)

        # Z-score normalization
        normalized = (df - df.mean()) / (df.std() + 1e-8)

        return normalized
