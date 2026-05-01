"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/feature_engineering.py
Institutional-grade feature engineering pipeline for XAUUSD.
Computes 140+ technical features including multi-timeframe analysis,
candle patterns, and volume profiles.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd
import talib
from scipy.stats import linregress

from src.core.profiler import profile as profile_context

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Engineers technical features from raw OHLCV data.
    Implements multi-timeframe analysis and ensures no look-ahead bias.
    """

    def __init__(
        self,
        base_timeframe: str = "M5",
        timeframes: Optional[List[str]] = None,
        normalize: bool = True,
        method: str = "zscore",
    ):
        """
        Initialize the FeatureEngineer.

        Args:
            base_timeframe: The timeframe of the input DataFrame.
            timeframes: List of timeframes for multi-timeframe features.
            normalize: Whether to normalize the output feature matrix.
            method: Normalization method ('zscore' or 'minmax').
        """
        self.base_timeframe = base_timeframe
        self.timeframes = timeframes or ["M1", "M5", "M15", "H1", "H4", "D1"]
        self.normalize = normalize
        self.method = method
        self.feature_columns: List[str] = []

        # Normalization stats
        self.means: Optional[pd.Series] = None
        self.stds: Optional[pd.Series] = None
        self.mins: Optional[pd.Series] = None
        self.maxs: Optional[pd.Series] = None

    def compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute all features for the given OHLCV DataFrame.

        Args:
            df: Input DataFrame with 'open', 'high', 'low', 'close', 'tick_volume'.

        Returns:
            DataFrame containing the engineered features.
        """
        with profile_context("compute_features"):
            if df.empty:
                return pd.DataFrame()

            # Ensure column names are lowercase
            df = df.copy()
            df.columns = [col.lower() for col in df.columns]

            # 1. Base Timeframe Features
            feature_blocks = []
            feature_blocks.append(self._get_technical_indicators(df, prefix=f"base_{self.base_timeframe}"))
            feature_blocks.append(self._get_candle_patterns(df))
            feature_blocks.append(self._get_price_action_features(df))
            feature_blocks.append(self._get_volume_features(df))

            # 2. Multi-Timeframe Features
            for tf in self.timeframes:
                if tf == self.base_timeframe:
                    continue
                mtf_features = self._compute_mtf_features(df, tf)
                feature_blocks.append(mtf_features)

            # Concatenate all blocks to avoid fragmentation
            full_df = pd.concat([df] + feature_blocks, axis=1)

            # Drop rows with NaNs resulting from indicator windows
            full_df = full_df.dropna()

            # Remove original OHLCV columns for the final feature matrix
            features_only = full_df.drop(columns=["open", "high", "low", "close", "tick_volume"])

            # Also drop any 'real_volume' if present
            if "real_volume" in features_only.columns:
                features_only = features_only.drop(columns=["real_volume"])

            if self.normalize:
                features_only = self._normalize_features(features_only)

            self.feature_columns = features_only.columns.tolist()
            return features_only

    def _get_technical_indicators(self, df: pd.DataFrame, prefix: str) -> pd.DataFrame:
        """Compute standard technical indicators."""
        indicators = {}
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        volume = df["tick_volume"].values.astype(float)

        # Momentum
        indicators[f"{prefix}_rsi"] = talib.RSI(close, timeperiod=14)

        macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        indicators[f"{prefix}_macd"] = macd
        indicators[f"{prefix}_macd_signal"] = macdsignal
        indicators[f"{prefix}_macd_hist"] = macdhist

        # Volatility
        indicators[f"{prefix}_atr"] = talib.ATR(high, low, close, timeperiod=14)
        upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        indicators[f"{prefix}_bb_upper"] = upper
        indicators[f"{prefix}_bb_middle"] = middle
        indicators[f"{prefix}_bb_lower"] = lower
        indicators[f"{prefix}_bb_width"] = (upper - lower) / (middle + 1e-8)

        # EMA Stacks
        for period in [8, 21, 50, 200]:
            indicators[f"{prefix}_ema_{period}"] = talib.EMA(close, timeperiod=period)
            # Distance from EMA
            indicators[f"{prefix}_dist_ema_{period}"] = (close - indicators[f"{prefix}_ema_{period}"]) / (indicators[f"{prefix}_ema_{period}"] + 1e-8)

        # ADX
        indicators[f"{prefix}_adx"] = talib.ADX(high, low, close, timeperiod=14)

        # Stochastic
        slowk, slowd = talib.STOCH(high, low, close, fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)
        indicators[f"{prefix}_stoch_k"] = slowk
        indicators[f"{prefix}_stoch_d"] = slowd

        return pd.DataFrame(indicators, index=df.index)

    def _get_candle_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all TA-Lib candle patterns."""
        op = df["open"].values
        hi = df["high"].values
        lo = df["low"].values
        cl = df["close"].values

        patterns = {}
        pattern_list = talib.get_function_groups()["Pattern Recognition"]
        for pattern in pattern_list:
            patterns[f"pattern_{pattern.lower()}"] = getattr(talib, pattern)(op, hi, lo, cl)

        return pd.DataFrame(patterns, index=df.index)

    def _get_price_action_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute custom price action features."""
        pa = {}
        close = df["close"]

        # Returns
        pa["returns_1"] = close.pct_change(1)
        pa["returns_5"] = close.pct_change(5)

        # Log returns
        pa["log_returns"] = np.log(close / close.shift(1).replace(0, 1e-8))

        # Range
        pa["day_range"] = (df["high"] - df["low"]) / df["close"].replace(0, 1e-8)
        pa["body_size"] = (df["close"] - df["open"]).abs() / (df["high"] - df["low"]).replace(0, 1e-8)

        # Slope (Linear Regression)
        def get_slope(series: pd.Series) -> float:
            if series.isna().any():
                return 0.0
            y = series.values
            x = np.arange(len(y))
            slope, _, _, _, _ = linregress(x, y)
            return slope

        pa["slope_5"] = close.rolling(window=5).apply(get_slope, raw=False)
        pa["slope_20"] = close.rolling(window=20).apply(get_slope, raw=False)

        return pd.DataFrame(pa, index=df.index)

    def _get_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute volume-based features."""
        vol = {}
        volume = df["tick_volume"]

        vol["vol_sma_20"] = volume / volume.rolling(window=20).mean().replace(0, 1e-8)
        vol["obv"] = talib.OBV(df["close"].values, volume.values.astype(float))

        return pd.DataFrame(vol, index=df.index)

    def _compute_mtf_features(self, df: pd.DataFrame, tf: str) -> pd.DataFrame:
        """
        Resample data to a different timeframe and compute features.
        Ensures no look-ahead bias by shifting.
        """
        # Map MT5-style timeframe strings to Pandas frequency strings
        tf_map = {
            "M1": "1min", "M5": "5min", "M15": "15min", "M30": "30min",
            "H1": "1h", "H4": "4h", "D1": "1D", "W1": "1W", "MN1": "1ME"
        }
        freq = tf_map.get(tf, tf)

        # Resample
        resampled = df.resample(freq).agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "tick_volume": "sum"
        }).dropna()

        # Compute indicators on resampled data
        mtf_indicators = self._get_technical_indicators(resampled, prefix=f"mtf_{tf}")

        # Shift to avoid look-ahead bias
        # The feature at time T must only use data available BEFORE T.
        mtf_indicators = mtf_indicators.shift(1)

        # Reindex to original DataFrame
        mtf_indicators = mtf_indicators.reindex(df.index).ffill()

        return mtf_indicators

    def _normalize_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize the feature matrix."""
        if self.method == "zscore":
            if self.means is None:
                self.means = df.mean()
                self.stds = df.std().replace(0, 1)
            return (df - self.means) / self.stds
        elif self.method == "minmax":
            if self.mins is None:
                self.mins = df.min()
                self.maxs = df.max()
            return (df - self.mins) / (self.maxs - self.mins).replace(0, 1)
        return df

    def get_feature_count(self) -> int:
        """Return the number of engineered features."""
        return len(self.feature_columns)
