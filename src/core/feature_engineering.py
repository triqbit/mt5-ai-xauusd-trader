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

try:
    import talib
except ImportError:
    talib = None

from src.core.profiler import profile as profile_context

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Institutional-grade feature engineering pipeline for financial time series.

    This class computes a comprehensive set of technical features including
    standard indicators, candle patterns, multi-timeframe analysis, and
    custom price action/volume features. It ensures data integrity by
    preventing look-ahead bias and providing normalization.
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
            base_timeframe (str): The timeframe of the input DataFrame (e.g., 'M5').
            timeframes (Optional[List[str]]): List of timeframes for multi-timeframe features.
                Defaults to ["M1", "M5", "M15", "H1", "H4", "D1"].
            normalize (bool): Whether to normalize the output feature matrix.
            method (str): Normalization method ('zscore' or 'minmax').
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
            df: Input DataFrame with 'open', 'high', 'low', 'close', 'volume'.
                Must have a DatetimeIndex.

        Returns:
            pd.DataFrame: Normalized feature matrix ready for model inference.
                The original OHLCV columns are removed.
        """
        with profile_context("compute_features"):
            if df.empty:
                return pd.DataFrame()

            # Ensure column names are lowercase and standardized
            df = df.copy()
            df.columns = [col.lower() for col in df.columns]

            # Standardize volume column name
            if "tick_volume" in df.columns:
                df = df.rename(columns={"tick_volume": "volume"})
            elif "vol" in df.columns:
                df = df.rename(columns={"vol": "volume"})

            if "volume" not in df.columns:
                logger.warning("Volume column not found. Creating dummy volume column.")
                df["volume"] = 1.0  # Use 1.0 to avoid division by zero if used as denominator

            # 1. Base Timeframe Features
            feature_blocks = []
            feature_blocks.append(
                self._get_technical_indicators(df, prefix=f"base_{self.base_timeframe}")
            )
            feature_blocks.append(self._get_candle_patterns(df))
            feature_blocks.append(self._get_price_action_features(df))
            feature_blocks.append(self._get_volume_features(df))

            # 2. Multi-Timeframe Features
            for tf in self.timeframes:
                if tf == self.base_timeframe:
                    continue
                mtf_features = self._compute_mtf_features(df, tf)
                feature_blocks.append(mtf_features)

            # Filter out empty DataFrames before concatenation
            feature_blocks = [fb for fb in feature_blocks if not fb.empty]

            # Concatenate all blocks to avoid fragmentation
            if not feature_blocks:
                return pd.DataFrame(index=df.index)

            full_df = pd.concat([df, *feature_blocks], axis=1)

            # Drop rows with NaNs resulting from indicator windows
            full_df = full_df.dropna()

            # Remove original OHLCV columns for the final feature matrix
            to_drop = ["open", "high", "low", "close", "volume", "tick_volume", "real_volume", "vol"]
            existing_to_drop = [col for col in to_drop if col in full_df.columns]
            features_only = full_df.drop(columns=existing_to_drop)

            if self.normalize:
                features_only = self._normalize_features(features_only)

            self.feature_columns = features_only.columns.tolist()
            return features_only

    def _get_technical_indicators(self, df: pd.DataFrame, prefix: str) -> pd.DataFrame:
        """
        Compute standard technical indicators using TA-Lib.

        Args:
            df: Input OHLCV DataFrame.
            prefix: String prefix for the feature names (e.g., 'base_M5').

        Returns:
            pd.DataFrame: DataFrame containing technical indicators.
        """
        if talib is None:
            logger.warning("TA-Lib not installed. Skipping technical indicators.")
            return pd.DataFrame(index=df.index)

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
        """
        Compute all available TA-Lib candle pattern recognition features.

        Args:
            df: Input OHLCV DataFrame.

        Returns:
            pd.DataFrame: DataFrame where each column is a candle pattern (values -100, 0, 100).
        """
        if talib is None:
            logger.warning("TA-Lib not installed. Skipping candle patterns.")
            return pd.DataFrame(index=df.index)

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
        """
        Compute custom price action features including returns and vectorized slopes.

        Args:
            df: Input OHLCV DataFrame.

        Returns:
            pd.DataFrame: DataFrame containing price action features.
        """
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
        This implementation is significantly faster than using rolling().apply().

        Args:
            series: Input price series.
            window: Rolling window size.

        Returns:
            pd.Series: Rolling slope values.
        """
        n = window
        if len(series) < n:
            return pd.Series(np.nan, index=series.index)

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
        """
        Compute volume-based features including rolling VWAP and VPT.

        Args:
            df: Input OHLCV DataFrame.

        Returns:
            pd.DataFrame: DataFrame containing volume-related features.
        """
        vol = {}
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        # Relative Volume (RVOL)
        vol["rvol_20"] = volume / volume.rolling(window=20).mean().replace(0, 1e-8)
        vol["rvol_100"] = volume / volume.rolling(window=100).mean().replace(0, 1e-8)

        # VWAP Approximation (Rolling) - A proxy for Volume Profile Value Areas
        typical_price = (high + low + close) / 3

        # Short-term VWAP
        vol["vwap_20"] = (typical_price * volume).rolling(window=20).sum() / volume.rolling(
            window=20
        ).sum().replace(0, 1e-8)
        vol["dist_vwap_20"] = (close - vol["vwap_20"]) / vol["vwap_20"].replace(0, 1e-8)

        # Medium-term VWAP
        vol["vwap_50"] = (typical_price * volume).rolling(window=50).sum() / volume.rolling(
            window=50
        ).sum().replace(0, 1e-8)
        vol["dist_vwap_50"] = (close - vol["vwap_50"]) / vol["vwap_50"].replace(0, 1e-8)

        # Volume Price Trend (VPT)
        vol["vpt"] = (volume * close.pct_change().fillna(0)).cumsum()

        if talib is not None:
            # Re-calculating as values to ensure they match index length if TA-Lib is mocked
            obv = talib.OBV(close.values, volume.values.astype(float))
            if len(obv) == len(df):
                vol["obv"] = obv

            mfi = talib.MFI(high.values, low.values, close.values, volume.values.astype(float), timeperiod=14)
            if len(mfi) == len(df):
                vol["mfi_14"] = mfi
        else:
            logger.warning("TA-Lib not installed. Skipping TA-Lib volume indicators.")

        return pd.DataFrame(vol, index=df.index)

    def _compute_mtf_features(self, df: pd.DataFrame, tf: str) -> pd.DataFrame:
        """
        Resample data to a different timeframe and compute technical indicators.

        Ensures no look-ahead bias by shifting resampled indicators forward by one
        period before reindexing back to the base timeframe.

        Args:
            df: Input OHLCV DataFrame at base timeframe.
            tf: Target timeframe string (e.g., 'H1').

        Returns:
            pd.DataFrame: Multi-timeframe features aligned to the base timeframe.
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
                    "volume": "sum",
                }
            )
            .dropna()
        )

        # Compute indicators on resampled data
        mtf_indicators = self._get_technical_indicators(resampled, prefix=f"mtf_{tf}")

        # Shift to avoid look-ahead bias
        # The feature at time T must only use data available BEFORE T.
        if not mtf_indicators.empty:
            mtf_indicators = mtf_indicators.shift(1)

        # Reindex to original DataFrame
        mtf_indicators = mtf_indicators.reindex(df.index).ffill()

        return mtf_indicators

    def _normalize_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize the feature matrix using Z-score or Min-Max scaling.

        Args:
            df: Input feature matrix.

        Returns:
            pd.DataFrame: Normalized feature matrix.
        """
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
        """
        Return the number of engineered features.

        Returns:
            int: Count of feature columns.
        """
        return len(self.feature_columns)
