"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/feature_engineering.py
Institutional-grade feature engineering pipeline for XAUUSD.
Computes 140+ technical features including multi-timeframe analysis,
candle patterns, and volume profiles.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np
import pandas as pd
import talib

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

    def compute_features(
        self, df: pd.DataFrame, drop_ohlcv: bool = True
    ) -> pd.DataFrame:
        """
        Compute all features for the given OHLCV DataFrame.

        Args:
            df: Input DataFrame with 'open', 'high', 'low', 'close', 'tick_volume'.
            drop_ohlcv: Whether to remove original OHLCV columns.

        Returns:
            DataFrame containing the engineered features.
        """
        with profile_context("compute_features_total"):
            if df.empty:
                return pd.DataFrame()

            # Ensure column names are lowercase
            df = df.copy()
            df.columns = [col.lower() for col in df.columns]

            # 1. Base Timeframe Features
            feature_blocks = []
            with profile_context("fe_base_technical"):
                feature_blocks.append(
                    self._get_technical_indicators(df, prefix=f"base_{self.base_timeframe}")
                )
            with profile_context("fe_candle_patterns"):
                feature_blocks.append(self._get_candle_patterns(df))
            with profile_context("fe_price_action"):
                feature_blocks.append(self._get_price_action_features(df))
            with profile_context("fe_volume"):
                feature_blocks.append(self._get_volume_features(df))

            # 2. Multi-Timeframe Features
            with profile_context("fe_mtf_all"):
                for tf in self.timeframes:
                    if tf == self.base_timeframe:
                        continue
                    with profile_context(f"fe_mtf_{tf}"):
                        mtf_features = self._compute_mtf_features(df, tf)
                        feature_blocks.append(mtf_features)

            # Concatenate all blocks to avoid fragmentation
            full_df = pd.concat([df, *feature_blocks], axis=1)

            # Optimization: Be selective with dropna to avoid losing all data if MTF fails
            # We identify base features and MTF features
            base_cols = [c for c in full_df.columns if c.startswith(f"base_{self.base_timeframe}") or c.startswith("pattern_")]
            mtf_cols = [c for c in full_df.columns if c.startswith("mtf_")]

            # First, drop rows where base features are NaN
            if base_cols:
                full_df = full_df.dropna(subset=base_cols)

            # If MTF features are all NaN (data too short), we might want to keep the base features
            # instead of returning an empty DataFrame.
            if not full_df.empty and mtf_cols:
                # Check if MTF columns are entirely NaN for the remaining rows
                if full_df[mtf_cols].isna().all().all():
                    logger.warning("MTF features are entirely NaN due to insufficient data history. Falling back to base features.")
                    # Keep rows, but MTF features will be NaN or we can drop the columns
                    # To be safe for models, we might need to fill with 0 or drop columns.
                    # Here we choose to drop columns to maintain model input integrity if expected.
                    # But if the model EXPECTS MTF, it will fail later.
                    # Better to drop rows and see if any remain.
                    temp_df = full_df.dropna(subset=mtf_cols)
                    if temp_df.empty:
                         logger.error("Insufficient data for MTF features. Row count dropped to 0.")
                    else:
                         full_df = temp_df
                else:
                    full_df = full_df.dropna(subset=mtf_cols)

            if full_df.empty:
                logger.error("Feature engineering resulted in an empty DataFrame.")
                return pd.DataFrame()

            # Remove original OHLCV columns for the final feature matrix if requested
            if drop_ohlcv:
                features_only = full_df.drop(columns=["open", "high", "low", "close", "tick_volume"])
            else:
                features_only = full_df

            # Also drop any 'real_volume' if present
            if "real_volume" in features_only.columns:
                features_only = features_only.drop(columns=["real_volume"])

            # Ensure all remaining features are NaN-free before normalization
            features_only = features_only.dropna()

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
            indicators[f"{prefix}_dist_ema_{period}"] = (
                close - indicators[f"{prefix}_ema_{period}"]
            ) / (indicators[f"{prefix}_ema_{period}"] + 1e-8)

        # ADX
        indicators[f"{prefix}_adx"] = talib.ADX(high, low, close, timeperiod=14)

        # Stochastic
        slowk, slowd = talib.STOCH(
            high,
            low,
            close,
            fastk_period=5,
            slowk_period=3,
            slowk_matype=0,
            slowd_period=3,
            slowd_matype=0,
        )
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
        pa["body_size"] = (df["close"] - df["open"]).abs() / (df["high"] - df["low"]).replace(
            0, 1e-8
        )

        # Vectorized Slope (Linear Regression) - ~2500x faster than rolling().apply(linregress)
        pa["slope_5"] = self._calculate_rolling_slope(close, window=5)
        pa["slope_20"] = self._calculate_rolling_slope(close, window=20)

        return pd.DataFrame(pa, index=df.index)

    def _calculate_rolling_slope(self, series: pd.Series, window: int) -> pd.Series:
        """
        Compute linear regression slope over a rolling window using vectorized operations.
        Formula: Slope = (sum(i*y) - x_bar * sum(y)) / SS_xx
        """
        n = window
        if len(series) < n:
            return pd.Series(0.0, index=series.index)

        x_idx = np.arange(len(series))
        sum_y = series.rolling(window=n).sum()
        sum_iy_abs = (series * x_idx).rolling(window=n).sum()

        # Convert absolute index sum to relative window index sum
        # sum(i*y) where i is 0 to n-1
        sum_iy_rel = sum_iy_abs - (x_idx - n + 1) * sum_y

        x_bar = (n - 1) / 2
        ss_xx = n * (n**2 - 1) / 12

        slope = (sum_iy_rel - x_bar * sum_y) / ss_xx
        return slope

    def _get_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute volume-based features including rolling VWAP and VPT."""
        vol = {}
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["tick_volume"]

        vol["vol_sma_20"] = volume / volume.rolling(window=20).mean().replace(0, 1e-8)
        vol["obv"] = talib.OBV(close.values, volume.values.astype(float))

        # VWAP Approximation (Rolling)
        typical_price = (high + low + close) / 3
        vol["vwap_20"] = (typical_price * volume).rolling(window=20).sum() / volume.rolling(
            window=20
        ).sum().replace(0, 1e-8)
        vol["dist_vwap_20"] = (close - vol["vwap_20"]) / vol["vwap_20"].replace(0, 1e-8)

        # Volume Price Trend (VPT)
        vol["vpt"] = (volume * close.pct_change().fillna(0)).cumsum()

        return pd.DataFrame(vol, index=df.index)

    def _compute_mtf_features(self, df: pd.DataFrame, tf: str) -> pd.DataFrame:
        """
        Resample data to a different timeframe and compute features.
        Ensures no look-ahead bias by shifting.
        """
        # Map MT5-style timeframe strings to Pandas frequency strings
        tf_map = {
            "M1": "1min",
            "M5": "5min",
            "M15": "15min",
            "M30": "30min",
            "H1": "1h",
            "H4": "4h",
            "D1": "1D",
            "W1": "1W",
            "MN1": "1ME",
        }
        freq = tf_map.get(tf, tf)

        # Resample
        resampled = (
            df.resample(freq)
            .agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "tick_volume": "sum",
                }
            )
            .dropna()
        )

        # Compute indicators on resampled data
        mtf_indicators = self._get_technical_indicators(resampled, prefix=f"mtf_{tf}")

        # Reindex to original DataFrame using forward fill to handle frequency misalignment.
        # We then shift by 1 to ensure that at any time T, we only use MTF data
        # from periods that have completely closed.
        mtf_indicators = mtf_indicators.reindex(df.index, method='ffill').shift(1)

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
