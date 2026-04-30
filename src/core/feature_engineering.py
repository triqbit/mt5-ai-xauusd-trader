"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/feature_engineering.py
Compute 140+ features from raw OHLCV data using TA-Lib.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd

try:
    import talib
except ImportError:
    talib = None

logger = logging.getLogger(__name__)

class FeatureEngineer:
    """
    Computes technical indicators and patterns for XAUUSD trading.
    Supports multi-timeframe analysis and feature normalization.
    """

    def __init__(self, base_timeframe: str = "M5"):
        """
        Initialize the FeatureEngineer.

        Args:
            base_timeframe: The timeframe of the input DataFrame (e.g., 'M1', 'M5').
        """
        if talib is None:
            logger.error("TA-Lib not installed. Feature engineering will fail.")

        self.base_timeframe = base_timeframe
        self.feature_names: List[str] = []

    def compute_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute all features for the given OHLCV DataFrame.

        Args:
            df: DataFrame with ['open', 'high', 'low', 'close', 'volume'] columns.

        Returns:
            pd.DataFrame: A DataFrame containing all computed features.
        """
        self._validate_input(df)

        df = df.copy()
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)

        # 1. Core Technical Indicators
        df = self._add_core_indicators(df)

        # 2. Candle Patterns
        df = self._add_candle_patterns(df)

        # 3. Volume Profile
        df = self._add_volume_features(df)

        # 4. Multi-timeframe Features
        df = self._add_multi_timeframe_features(df)

        # 5. Additional indicators to reach 140+ features
        df = self._add_extra_indicators(df)

        # Cleanup
        df = df.replace([np.inf, -np.inf], np.nan).ffill().fillna(0)

        self.feature_names = df.columns.tolist()
        return df

    def _validate_input(self, df: pd.DataFrame):
        """Ensure required columns exist."""
        required = ['open', 'high', 'low', 'close', 'volume']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Input DataFrame missing required columns: {missing}")

    def _add_core_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add core technical indicators: RSI, MACD, ATR, BB, EMAs."""
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values

        # RSI
        df['rsi_14'] = talib.RSI(close, timeperiod=14)
        df['rsi_7'] = talib.RSI(close, timeperiod=7)

        # MACD
        macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        df['macd'] = macd
        df['macd_signal'] = macdsignal
        df['macd_hist'] = macdhist

        # ATR
        df['atr_14'] = talib.ATR(high, low, close, timeperiod=14)

        # Bollinger Bands
        upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        df['bb_upper'] = upper
        df['bb_middle'] = middle
        df['bb_lower'] = lower
        df['bb_width'] = (upper - lower) / middle

        # EMA Stacks
        for p in [8, 21, 50, 200]:
            df[f'ema_{p}'] = talib.EMA(close, timeperiod=p)
            # Distance from EMA
            df[f'dist_ema_{p}'] = (close - df[f'ema_{p}']) / df[f'ema_{p}']

        return df

    def _add_candle_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add candle pattern recognition using TA-Lib."""
        op = df['open'].values
        hi = df['high'].values
        lo = df['low'].values
        cl = df['close'].values

        # Get all CDL functions from TA-Lib
        cdl_functions = [f for f in dir(talib) if f.startswith('CDL')]

        for func_name in cdl_functions:
            func = getattr(talib, func_name)
            # Result is usually -100, 0, or 100
            df[func_name.lower()] = func(op, hi, lo, cl)

        return df

    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based features."""
        cl = df['close'].values
        hi = df['high'].values
        lo = df['low'].values
        vo = df['volume'].values

        df['obv'] = talib.OBV(cl, vo)
        df['adline'] = talib.AD(hi, lo, cl, vo)
        df['adosc'] = talib.ADOSC(hi, lo, cl, vo, fastperiod=3, slowperiod=10)
        df['mfi'] = talib.MFI(hi, lo, cl, vo, timeperiod=14)

        # Volume EMA
        df['volume_ema_20'] = talib.EMA(vo, timeperiod=20)
        df['volume_ratio'] = vo / (df['volume_ema_20'] + 1e-8)

        # Approximate Volume-Weighted Price distance
        vwap_approx = (cl * vo).cumsum() / (vo.cumsum() + 1e-8)
        df['dist_vwap_approx'] = (cl - vwap_approx) / vwap_approx

        for p in [5, 10, 30, 50]:
            df[f'volume_ema_{p}'] = talib.EMA(vo, timeperiod=p)
            df[f'volume_ratio_{p}'] = vo / (df[f'volume_ema_{p}'] + 1e-8)

        return df

    def _add_multi_timeframe_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add multi-timeframe features (M15, H1, H4, D1)."""
        if not isinstance(df.index, pd.DatetimeIndex):
            # If not datetime index, MTF resampling won't work easily
            logger.warning("DataFrame index is not DatetimeIndex. Skipping MTF features.")
            return df

        base_df = df[['open', 'high', 'low', 'close', 'volume']]

        # Decide which timeframes to include based on base_timeframe
        if self.base_timeframe.upper() == "M1":
            timeframes = ["5min", "15min", "1h", "4h", "1D"]
        else:
            timeframes = ["15min", "1h", "4h", "1D"]

        for tf in timeframes:
            # Resample to higher timeframe
            resampled = base_df.resample(tf).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()

            # Compute some basic features on resampled data
            resampled[f'rsi_14_{tf}'] = talib.RSI(resampled['close'].values, timeperiod=14)
            resampled[f'ema_20_{tf}'] = talib.EMA(resampled['close'].values, timeperiod=20)

            # Shift resampled data to avoid look-ahead bias (leakage)
            # The value at time t should only depend on data available strictly before t
            resampled_shifted = resampled[[f'rsi_14_{tf}', f'ema_20_{tf}']].shift(1)

            # Reindex back to base timeframe
            resampled_reindexed = resampled_shifted.reindex(df.index, method='ffill')

            # Add to main df
            df = pd.concat([df, resampled_reindexed], axis=1)

            # Add distance to higher timeframe EMA
            df[f'dist_ema_20_{tf}'] = (df['close'] - df[f'ema_20_{tf}']) / df[f'ema_20_{tf}']

        return df

    def _add_extra_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add additional indicators to reach 140+ features."""
        cl = df['close'].values
        hi = df['high'].values
        lo = df['low'].values

        # Additional timeperiods for existing indicators
        for p in [10, 20, 30, 50, 100]:
            df[f'rsi_{p}'] = talib.RSI(cl, timeperiod=p)
            df[f'atr_{p}'] = talib.ATR(hi, lo, cl, timeperiod=p)
            df[f'ema_{p}'] = talib.EMA(cl, timeperiod=p)

        # Price shifts and returns
        for s in [1, 2, 3, 5, 10]:
            df[f'return_{s}'] = df['close'].pct_change(s)
            df[f'log_return_{s}'] = np.log(df['close'] / df['close'].shift(s))

        # Momentum Indicators
        df['adx'] = talib.ADX(hi, lo, cl, timeperiod=14)
        df['plus_di'] = talib.PLUS_DI(hi, lo, cl, timeperiod=14)
        df['minus_di'] = talib.MINUS_DI(hi, lo, cl, timeperiod=14)
        df['cci'] = talib.CCI(hi, lo, cl, timeperiod=14)
        df['mom'] = talib.MOM(cl, timeperiod=10)
        df['roc'] = talib.ROC(cl, timeperiod=10)

        # Stochastic
        slowk, slowd = talib.STOCH(hi, lo, cl, fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)
        df['stoch_k'] = slowk
        df['stoch_d'] = slowd

        # Volatility
        df['natr'] = talib.NATR(hi, lo, cl, timeperiod=14)
        df['trange'] = talib.TRANGE(hi, lo, cl)

        # Price transformations / cycle
        df['ht_trendline'] = talib.HT_TRENDLINE(cl)

        return df

    def normalize_features(self, df: pd.DataFrame, method: str = "zscore") -> pd.DataFrame:
        """
        Normalize the feature matrix.

        Args:
            df: Feature DataFrame.
            method: 'zscore' or 'minmax'.

        Returns:
            pd.DataFrame: Normalized features.
        """
        if method == "zscore":
            return (df - df.mean()) / (df.std() + 1e-8)
        elif method == "minmax":
            return (df - df.min()) / (df.max() - df.min() + 1e-8)
        else:
            raise ValueError(f"Unknown normalization method: {method}")
