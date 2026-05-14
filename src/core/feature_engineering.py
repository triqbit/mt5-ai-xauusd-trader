"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/feature_engineering.py
Institutional-grade feature engineering pipeline for XAUUSD.
Computes 140+ technical features including multi-timeframe analysis,
candle patterns, and volume profiles.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

try:
    import talib

    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False
    talib = None

from src.core.profiler import profile

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Engineers technical features from raw OHLCV data.
    Implements multi-timeframe analysis and ensures no look-ahead bias.
    Supports stateful normalization for production inference.
    """

    # Pre-cache TA-Lib pattern functions to avoid redundant lookups
    _PATTERN_FUNCS = (
        {
            name.lower(): getattr(talib, name)
            for name in talib.get_function_groups()["Pattern Recognition"]
        }
        if HAS_TALIB
        else {}
    )

    def __init__(
        self,
        base_timeframe: str = "M5",
        timeframes: list[str] | None = None,
        normalize: bool = True,
        method: str = "zscore",
        include_mtf_patterns: bool = False,
        include_volume_profile: bool = True,
    ):
        """
        Initialize the FeatureEngineer.

        Args:
            base_timeframe: The timeframe of the input DataFrame (e.g., 'M5').
            timeframes: List of timeframes for multi-timeframe features.
            normalize: Whether to normalize the output feature matrix.
            method: Normalization method ('zscore' or 'minmax').
            include_mtf_patterns: Whether to compute candle patterns for MTF data (slow).
            include_volume_profile: Whether to compute expensive volume profile features.
        """
        self.base_timeframe = base_timeframe
        self.timeframes = timeframes or ["M1", "M5", "M15", "H1", "H4", "D1"]
        self.normalize = normalize
        self.method = method
        self.include_mtf_patterns = include_mtf_patterns
        self.include_volume_profile = include_volume_profile
        self.feature_columns: list[str] = []

        # Normalization stats
        self.means: np.ndarray | None = None
        self.stds: np.ndarray | None = None
        self.mins: np.ndarray | None = None
        self.maxs: np.ndarray | None = None

    def compute_features(self, df: pd.DataFrame, drop_ohlcv: bool = True) -> pd.DataFrame:
        """
        Compute all features for the given OHLCV DataFrame.

        Args:
            df: Input DataFrame with 'open', 'high', 'low', 'close', 'tick_volume'.
            drop_ohlcv: Whether to remove original OHLCV columns.

        Returns:
            DataFrame containing the engineered features.
        """
        with profile("compute_features_total"):
            if df.empty:
                return pd.DataFrame()

            # Ensure lower case columns for consistency
            df = df.rename(columns=str.lower)

            # 1. Base Timeframe Features
            all_features = {}
            prefix = f"base_{self.base_timeframe}"

            with profile("fe_base_technical"):
                all_features.update(self._get_technical_indicators(df, prefix=prefix))
            with profile("fe_candle_patterns"):
                all_features.update(self._get_candle_patterns(df))
            with profile("fe_price_action"):
                all_features.update(self._get_price_action_features(df))
            with profile("fe_volume"):
                all_features.update(self._get_volume_features(df))

            # Convert base features to DataFrame once
            base_features_df = pd.DataFrame(all_features, index=df.index)

            # 2. Multi-Timeframe Features
            mtf_blocks = []
            with profile("fe_mtf_all", slow_threshold_ms=100.0):
                for tf in self.timeframes:
                    if tf == self.base_timeframe:
                        continue
                    with profile(f"fe_mtf_{tf}", slow_threshold_ms=25.0):
                        mtf_features = self._compute_mtf_features(df, tf)
                        if not mtf_features.empty:
                            mtf_blocks.append(mtf_features)

            # Concatenate all blocks
            if mtf_blocks:
                full_df = pd.concat([df, base_features_df, *mtf_blocks], axis=1)
            else:
                full_df = pd.concat([df, base_features_df], axis=1)

            # Optimization: Cast to float32 for efficiency
            # Note: Pandas 3.0+ deprecated copy=False in astype, using default behavior
            full_df = full_df.astype(np.float32)

            # Identify columns
            ohlcv_cols = ["open", "high", "low", "close", "tick_volume", "real_volume"]
            base_feature_cols = [c for c in base_features_df.columns if c not in ohlcv_cols]

            # If volume profile is disabled, these are all NaNs and shouldn't trigger dropna
            if not self.include_volume_profile:
                vol_cols = ["vp_poc", "vp_vah", "vp_val", "vp_width"]
                base_feature_cols = [c for c in base_feature_cols if c not in vol_cols]

            # Resilience Improvement: Only drop NaNs from BASE features.
            # MTF features often have huge gaps (e.g. D1 on M5 data).
            # We forward-fill MTF and zero-fill remaining to maximize data utilization.
            features_only = full_df.dropna(subset=base_feature_cols).copy()

            # Identify all feature columns for consistent reindexing later
            feature_cols = [c for c in features_only.columns if c not in ohlcv_cols]

            # Forward fill then zero fill MTF gaps
            if not self.include_volume_profile:
                # Exclude volume profile from zero-fill to preserve NaNs for schema stability
                vol_cols = ["vp_poc", "vp_vah", "vp_val", "vp_width"]
                other_feature_cols = [c for c in feature_cols if c not in vol_cols]
                features_only[other_feature_cols] = (
                    features_only[other_feature_cols].ffill().fillna(0.0)
                )
            else:
                features_only[feature_cols] = features_only[feature_cols].ffill().fillna(0.0)

            if features_only.empty:
                logger.error(
                    "Feature engineering resulted in an empty DataFrame. Ensure input data has sufficient history."
                )
                return pd.DataFrame()

            # Remove original OHLCV columns if requested
            if drop_ohlcv:
                features_only = features_only.drop(
                    columns=[c for c in ohlcv_cols if c in features_only.columns]
                )

            # Ensure consistent column ordering
            if not self.feature_columns:
                self.feature_columns = features_only.columns.tolist()
            else:
                # Reindex to match the columns we have stats for, fill missing with 0
                features_only = features_only.reindex(columns=self.feature_columns).fillna(0.0)

            if self.normalize:
                with profile("fe_normalization"):
                    features_only = self._normalize_features(features_only)

            return features_only

    def _get_technical_indicators(self, df: pd.DataFrame, prefix: str) -> dict[str, np.ndarray]:
        """
        Compute standard technical indicators including RSI, MACD, ATR, and BBands.

        Args:
            df: Input DataFrame with OHLCV data.
            prefix: Prefix to prepend to all indicator column names.

        Returns:
            Dictionary containing computed technical indicators.
        """
        indicators = {}
        close = df["close"].values.astype(np.float64, copy=False)
        high = df["high"].values.astype(np.float64, copy=False)
        low = df["low"].values.astype(np.float64, copy=False)
        volume = df["tick_volume"].values.astype(np.float64, copy=False)

        if not HAS_TALIB:
            logger.warning("TA-Lib not installed. Technical indicators will be empty.")
            return indicators

        # Momentum
        indicators[f"{prefix}_rsi"] = talib.RSI(close, timeperiod=14)
        indicators[f"{prefix}_mfi"] = talib.MFI(high, low, close, volume, timeperiod=14)
        indicators[f"{prefix}_cci"] = talib.CCI(high, low, close, timeperiod=14)
        indicators[f"{prefix}_mom"] = talib.MOM(close, timeperiod=10)

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

        # Institutional Channels
        indicators[f"{prefix}_donchian_high"] = talib.MAX(high, timeperiod=20)
        indicators[f"{prefix}_donchian_low"] = talib.MIN(low, timeperiod=20)
        indicators[f"{prefix}_donchian_mid"] = (
            indicators[f"{prefix}_donchian_high"] + indicators[f"{prefix}_donchian_low"]
        ) / 2

        kc_mid = talib.EMA(close, timeperiod=20)
        kc_range = talib.ATR(high, low, close, timeperiod=20)
        indicators[f"{prefix}_keltner_upper"] = kc_mid + (2 * kc_range)
        indicators[f"{prefix}_keltner_lower"] = kc_mid - (2 * kc_range)

        # EMA Stacks (8/21/50/200)
        for period in [8, 21, 50, 200]:
            ema = talib.EMA(close, timeperiod=period)
            indicators[f"{prefix}_ema_{period}"] = ema
            indicators[f"{prefix}_dist_ema_{period}"] = (close - ema) / (ema + 1e-8)

        # Hilbert Transform
        indicators[f"{prefix}_ht_trendline"] = talib.HT_TRENDLINE(close)
        indicators[f"{prefix}_ht_sine"], indicators[f"{prefix}_ht_leadsine"] = talib.HT_SINE(close)
        indicators[f"{prefix}_ht_trendmode"] = talib.HT_TRENDMODE(close).astype(np.float64)

        return indicators

    def _get_candle_patterns(self, df: pd.DataFrame, prefix: str = "") -> dict[str, np.ndarray]:
        """
        Compute all available TA-Lib candle patterns.

        Args:
            df: Input DataFrame with OHLCV data.
            prefix: Optional prefix for pattern column names.

        Returns:
            Dictionary containing computed candle patterns.
        """
        patterns = {}
        if not HAS_TALIB:
            return patterns

        op = df["open"].values.astype(np.float64, copy=False)
        hi = df["high"].values.astype(np.float64, copy=False)
        lo = df["low"].values.astype(np.float64, copy=False)
        cl = df["close"].values.astype(np.float64, copy=False)

        col_prefix = f"{prefix}_pattern_" if prefix else "pattern_"
        for name, func in self._PATTERN_FUNCS.items():
            patterns[f"{col_prefix}{name}"] = func(op, hi, lo, cl).astype(np.float64)
        return patterns

    def _get_price_action_features(self, df: pd.DataFrame) -> dict[str, np.ndarray]:
        """
        Compute custom price action features like returns, ranges, and slopes.

        Args:
            df: Input DataFrame with OHLCV data.

        Returns:
            Dictionary containing custom price action features.
        """
        pa = {}
        close = df["close"].values.astype(np.float64, copy=False)
        high = df["high"].values.astype(np.float64, copy=False)
        low = df["low"].values.astype(np.float64, copy=False)
        open_ = df["open"].values.astype(np.float64, copy=False)

        if HAS_TALIB:
            pa["returns_1"] = talib.ROCP(close, timeperiod=1)
            pa["slope_20"] = talib.LINEARREG_SLOPE(close, timeperiod=20)
        else:
            # Fallback for returns if TA-Lib is missing
            pa["returns_1"] = (close / (np.roll(close, 1) + 1e-8)) - 1
            pa["returns_1"][0] = np.nan
            pa["slope_20"] = np.zeros_like(close)

        pa["log_returns"] = np.log(close / (np.roll(close, 1) + 1e-8))
        pa["log_returns"][0] = np.nan
        pa["day_range"] = (high - low) / (close + 1e-8)
        pa["body_size"] = np.abs(close - open_) / (high - low + 1e-8)
        return pa

    def _get_volume_features(self, df: pd.DataFrame) -> dict[str, np.ndarray]:
        """
        Compute volume-based features including Relative Volume and Volume Profile proxies.

        Args:
            df: Input DataFrame with OHLCV data.

        Returns:
            Dictionary containing volume-based features.
        """
        vol = {}
        close = df["close"].values.astype(np.float64, copy=False)
        high = df["high"].values.astype(np.float64, copy=False)
        low = df["low"].values.astype(np.float64, copy=False)
        volume = df["tick_volume"].values.astype(np.float64, copy=False)

        if HAS_TALIB:
            vol_sma_20 = talib.SMA(volume, timeperiod=20)
            vol["rvol"] = volume / (vol_sma_20 + 1e-8)
            vol["obv"] = talib.OBV(close, volume)

            # VWAP Approximation
            tp = (high + low + close) / 3
            tpv = tp * volume
            sum_tpv = talib.SUM(tpv, timeperiod=20)
            sum_v = talib.SUM(volume, timeperiod=20)
            vwap = sum_tpv / (sum_v + 1e-8)
            vol["dist_vwap_20"] = (close - vwap) / (vwap + 1e-8)
        else:
            # Fallback simple volume features
            vol_sma_20 = pd.Series(volume).rolling(20).mean().values
            vol["rvol"] = volume / (vol_sma_20 + 1e-8)
            vol["obv"] = np.zeros_like(close)
            vol["dist_vwap_20"] = np.zeros_like(close)

        # Volume-Weighted Price Distribution (Volume Profile Proxy)
        if self.include_volume_profile:
            window = 30
            try:
                # We use a rolling weighted average of price as a POC proxy
                # This is more accurate than a simple median as it incorporates volume
                rolling_poc = (pd.Series(close) * pd.Series(volume)).rolling(
                    window
                ).sum() / pd.Series(volume).rolling(window).sum()
                vol["vp_poc"] = rolling_poc.values

                # Simple quantiles for VAH/VAL
                rolling_close = pd.Series(close)
                vol["vp_vah"] = rolling_close.rolling(window).quantile(0.7).values
                vol["vp_val"] = rolling_close.rolling(window).quantile(0.3).values
                vol["vp_width"] = (vol["vp_vah"] - vol["vp_val"]) / (vol["vp_poc"] + 1e-8)
            except Exception:
                vol["vp_poc"] = np.full_like(close, np.nan)
                vol["vp_vah"] = np.full_like(close, np.nan)
                vol["vp_val"] = np.full_like(close, np.nan)
                vol["vp_width"] = np.full_like(close, np.nan)
        else:
            # Schema Stability: Populate with NaNs to ensure downstream consistency
            # while maintaining the performance benefit of skipping calculations.
            vol["vp_poc"] = np.full_like(close, np.nan)
            vol["vp_vah"] = np.full_like(close, np.nan)
            vol["vp_val"] = np.full_like(close, np.nan)
            vol["vp_width"] = np.full_like(close, np.nan)

        return vol

    def _compute_mtf_features(self, df: pd.DataFrame, tf: str) -> pd.DataFrame:
        """
        Resample data to a different timeframe and compute features with no look-ahead bias.

        Args:
            df: Input DataFrame at the base timeframe.
            tf: Target timeframe string (e.g., 'H1').

        Returns:
            DataFrame containing MTF features, reindexed to the base timeframe.
        """
        tf_map = {"M1": "1min", "M5": "5min", "M15": "15min", "H1": "1h", "H4": "4h", "D1": "1D"}
        freq = tf_map.get(tf, tf)

        # Resample to the target timeframe
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

        if resampled.empty:
            return pd.DataFrame()

        # Compute technical features and patterns on the resampled data
        mtf_all = {}
        prefix = f"mtf_{tf}"
        mtf_all.update(self._get_technical_indicators(resampled, prefix=prefix))

        if self.include_mtf_patterns:
            mtf_all.update(self._get_candle_patterns(resampled, prefix=prefix))

        combined_mtf = pd.DataFrame(mtf_all, index=resampled.index)

        # IMPORTANT: Shift forward to prevent look-ahead bias.
        # A 1-hour bar starting at 08:00 is only fully formed at 09:00.
        # By shifting 1, the features of the 08:00 bar are correctly associated with the 09:00 base-tf bar.
        combined_mtf = combined_mtf.shift(1)

        # Forward-fill to the base timeframe
        return combined_mtf.reindex(df.index, method="ffill")

    def _normalize_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize features using stored or newly computed stats.

        Args:
            df: DataFrame of features to normalize.

        Returns:
            Normalized DataFrame.
        """
        vals = df.values
        if self.method == "zscore":
            if self.means is None:
                self.means = np.nanmean(vals, axis=0)
                self.stds = np.nanstd(vals, axis=0)
                # Avoid division by zero
                self.stds[self.stds == 0] = 1.0
            norm_vals = (vals - self.means) / (self.stds + 1e-8)
            return pd.DataFrame(norm_vals, index=df.index, columns=df.columns)

        if self.method == "minmax":
            if self.mins is None:
                self.mins = np.nanmin(vals, axis=0)
                self.maxs = np.nanmax(vals, axis=0)
            denom = self.maxs - self.mins
            denom[denom == 0] = 1.0
            norm_vals = (vals - self.mins) / denom
            return pd.DataFrame(norm_vals, index=df.index, columns=df.columns)

        return df

    def get_normalization_stats(self) -> dict[str, Any]:
        """
        Retrieve normalization statistics for persistence.

        Returns:
            Dictionary containing method, means, stds, mins, maxs, and column names.
        """
        return {
            "method": self.method,
            "means": dict(zip(self.feature_columns, self.means.tolist(), strict=True))
            if self.means is not None
            else None,
            "stds": dict(zip(self.feature_columns, self.stds.tolist(), strict=True))
            if self.stds is not None
            else None,
            "mins": dict(zip(self.feature_columns, self.mins.tolist(), strict=True))
            if self.mins is not None
            else None,
            "maxs": dict(zip(self.feature_columns, self.maxs.tolist(), strict=True))
            if self.maxs is not None
            else None,
            "columns": self.feature_columns,
        }

    def set_normalization_stats(self, stats: dict[str, Any]) -> None:
        """
        Set normalization statistics from a previously saved state.

        Args:
            stats: Dictionary of normalization stats.
        """
        self.method = stats.get("method", self.method)
        cols = stats.get("columns", [])
        self.feature_columns = cols
        if stats.get("means"):
            self.means = np.array([stats["means"].get(c, 0.0) for c in cols])
        if stats.get("stds"):
            self.stds = np.array([stats["stds"].get(c, 1.0) for c in cols])
        if stats.get("mins"):
            self.mins = np.array([stats["mins"].get(c, 0.0) for c in cols])
        if stats.get("maxs"):
            self.maxs = np.array([stats["maxs"].get(c, 1.0) for c in cols])

    def get_feature_count(self) -> int:
        """Return the number of engineered features."""
        return len(self.feature_columns)
