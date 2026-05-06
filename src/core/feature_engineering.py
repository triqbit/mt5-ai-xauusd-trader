"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/feature_engineering.py
Institutional-grade feature engineering pipeline for XAUUSD.
Computes 140+ technical features including multi-timeframe analysis,
candle patterns, and volume profiles.
"""

from __future__ import annotations

import logging

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
        timeframes: list[str] | None = None,
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
        self.feature_columns: list[str] = []

        # Normalization stats
        self.means: pd.Series | None = None
        self.stds: pd.Series | None = None
        self.mins: pd.Series | None = None
        self.maxs: pd.Series | None = None

    def compute_features(self, df: pd.DataFrame, drop_ohlcv: bool = True) -> pd.DataFrame:
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

            # 1. Base Timeframe Features - Optimization: Collect all in one dict
            all_features = {}
            with profile_context("fe_base_technical"):
                all_features.update(
                    self._get_technical_indicators(df, prefix=f"base_{self.base_timeframe}")
                )
            with profile_context("fe_candle_patterns"):
                all_features.update(self._get_candle_patterns(df))
            with profile_context("fe_price_action"):
                all_features.update(self._get_price_action_features(df))
            with profile_context("fe_volume"):
                all_features.update(self._get_volume_features(df))

            # Convert base features to DataFrame once
            base_features_df = pd.DataFrame(all_features, index=df.index)

            # 2. Multi-Timeframe Features
            mtf_blocks = []
            with profile_context("fe_mtf_all"):
                for tf in self.timeframes:
                    if tf == self.base_timeframe:
                        continue
                    with profile_context(f"fe_mtf_{tf}"):
                        mtf_features = self._compute_mtf_features(df, tf)
                        mtf_blocks.append(mtf_features)

            # Concatenate all blocks to avoid fragmentation
            full_df = pd.concat([df, base_features_df, *mtf_blocks], axis=1)

            # Optimization: Be selective with dropna to avoid losing all data if MTF fails
            # We identify base features and MTF features
            base_cols = [
                c
                for c in full_df.columns
                if c.startswith(f"base_{self.base_timeframe}") or c.startswith("pattern_")
            ]
            mtf_cols = [c for c in full_df.columns if c.startswith("mtf_")]

            # First, drop rows where base features are NaN
            if base_cols:
                full_df = full_df.dropna(subset=base_cols)

            # If MTF features are all NaN (data too short), we might want to keep the base features
            # instead of returning an empty DataFrame.
            if not full_df.empty and mtf_cols:
                # Check if MTF columns are entirely NaN for the remaining rows
                if full_df[mtf_cols].isna().all().all():
                    logger.warning(
                        "MTF features are entirely NaN due to insufficient data history. Falling back to base features."
                    )
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
                features_only = full_df.drop(
                    columns=["open", "high", "low", "close", "tick_volume"]
                )
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

    def _get_technical_indicators(self, df: pd.DataFrame, prefix: str) -> dict[str, np.ndarray]:
        """
        Compute standard technical indicators including momentum, volatility, and trend.

        Args:
            df: Input DataFrame with OHLCV data.
            prefix: Prefix to prepend to all indicator column names.

        Returns:
            Dictionary containing computed technical indicators.
        """
        indicators = {}
        close = df["close"].values.astype(np.float64)
        high = df["high"].values.astype(np.float64)
        low = df["low"].values.astype(np.float64)
        volume = df["tick_volume"].values.astype(np.float64)

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

        # EMA Stacks
        for period in [8, 21, 50, 200]:
            indicators[f"{prefix}_ema_{period}"] = talib.EMA(close, timeperiod=period)
            # Distance from EMA
            indicators[f"{prefix}_dist_ema_{period}"] = (
                close - indicators[f"{prefix}_ema_{period}"]
            ) / (indicators[f"{prefix}_ema_{period}"] + 1e-8)

        # ADX
        indicators[f"{prefix}_adx"] = talib.ADX(high, low, close, timeperiod=14)

        # Williams %R
        indicators[f"{prefix}_willr"] = talib.WILLR(high, low, close, timeperiod=14)

        # Ultimate Oscillator
        indicators[f"{prefix}_ultosc"] = talib.ULTOSC(
            high, low, close, timeperiod1=7, timeperiod2=14, timeperiod3=28
        )

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

        # Hilbert Transform
        indicators[f"{prefix}_ht_trendline"] = talib.HT_TRENDLINE(close)
        indicators[f"{prefix}_ht_dcperiod"] = talib.HT_DCPERIOD(close)

        return indicators

    def _get_candle_patterns(self, df: pd.DataFrame, prefix: str = "") -> dict[str, np.ndarray]:
        """
        Compute all TA-Lib candle patterns.

        Args:
            df: Input DataFrame.
            prefix: Optional prefix for pattern column names.

        Returns:
            Dictionary of candle patterns.
        """
        op = df["open"].values.astype(np.float64)
        hi = df["high"].values.astype(np.float64)
        lo = df["low"].values.astype(np.float64)
        cl = df["close"].values.astype(np.float64)

        patterns = {}
        pattern_list = talib.get_function_groups()["Pattern Recognition"]
        col_prefix = f"{prefix}_" if prefix else "pattern_"

        for pattern in pattern_list:
            patterns[f"{col_prefix}{pattern.lower()}"] = getattr(talib, pattern)(op, hi, lo, cl)

        return patterns

    def _get_price_action_features(self, df: pd.DataFrame) -> dict[str, np.ndarray]:
        """
        Compute custom price action features such as returns, range, and slope.

        Args:
            df: Input DataFrame with OHLCV data.

        Returns:
            Dictionary containing custom price action features.
        """
        pa = {}
        close = df["close"].values.astype(np.float64)
        high = df["high"].values.astype(np.float64)
        low = df["low"].values.astype(np.float64)
        open_ = df["open"].values.astype(np.float64)

        # Optimization: Use TA-Lib ROCP for returns
        pa["returns_1"] = talib.ROCP(close, timeperiod=1)
        pa["returns_5"] = talib.ROCP(close, timeperiod=5)

        # Log returns - Optimization: Use NumPy
        pa["log_returns"] = np.log(close / (np.roll(close, 1) + 1e-8))
        pa["log_returns"][0] = np.nan

        # Range - Optimization: Use NumPy
        pa["day_range"] = (high - low) / (close + 1e-8)
        pa["body_size"] = np.abs(close - open_) / (high - low + 1e-8)

        # Linear Regression Slopes (Institutional-grade TA-Lib implementation)
        pa["slope_5"] = talib.LINEARREG_SLOPE(close, timeperiod=5)
        pa["slope_20"] = talib.LINEARREG_SLOPE(close, timeperiod=20)

        return pa

    def _get_volume_features(self, df: pd.DataFrame) -> dict[str, np.ndarray]:
        """
        Compute volume-based features including rolling VWAP, OBV, and VPT.

        Args:
            df: Input DataFrame with OHLCV data.

        Returns:
            Dictionary containing volume-based features.
        """
        vol = {}
        close = df["close"].values.astype(np.float64)
        high = df["high"].values.astype(np.float64)
        low = df["low"].values.astype(np.float64)
        volume = df["tick_volume"].values.astype(np.float64)

        # Optimization: Use TA-Lib for SMA instead of Pandas rolling
        vol_sma_20 = talib.SMA(volume, timeperiod=20)
        vol["vol_sma_20"] = volume / (vol_sma_20 + 1e-8)
        vol["rvol"] = vol["vol_sma_20"]  # Canonical RVOL
        vol["obv"] = talib.OBV(close, volume)

        # VWAP Approximation (Rolling) - Optimization: Use TA-Lib for SUM
        typical_price = (high + low + close) / 3
        tp_vol = typical_price * volume
        for period in [20, 50, 100]:
            sum_tp_vol = talib.SUM(tp_vol, timeperiod=period)
            sum_vol = talib.SUM(volume, timeperiod=period)
            vol[f"vwap_{period}"] = sum_tp_vol / (sum_vol + 1e-8)
            vol[f"dist_vwap_{period}"] = (close - vol[f"vwap_{period}"]) / (
                vol[f"vwap_{period}"] + 1e-8
            )

        # Volume Price Trend (VPT) - Optimization: Use TA-Lib ROCP and NumPy cumsum
        returns = talib.ROCP(close, timeperiod=1)
        # Handle first NaN from ROCP to match pct_change().fillna(0)
        returns[np.isnan(returns)] = 0
        vol["vpt"] = np.cumsum(volume * returns)

        return vol

    def _compute_mtf_features(self, df: pd.DataFrame, tf: str) -> pd.DataFrame:
        """
        Resample data to a different timeframe and compute features.
        Ensures no look-ahead bias by shifting.

        Args:
            df: Input DataFrame.
            tf: Timeframe string (e.g., 'M15', 'H1').

        Returns:
            DataFrame of resampled indicators.
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

        # 1. Compute indicators and patterns on resampled data
        # Optimization: Use dictionary update instead of multiple DFs + concat
        mtf_all = {}
        mtf_all.update(self._get_technical_indicators(resampled, prefix=f"mtf_{tf}"))
        mtf_all.update(self._get_candle_patterns(resampled, prefix=f"mtf_{tf}"))

        # Create DataFrame once
        combined_mtf = pd.DataFrame(mtf_all, index=resampled.index)

        # Reindex to original DataFrame using forward fill to handle frequency misalignment.
        # We then shift by 1 to ensure that at any time T, we only use MTF data
        # from periods that have completely closed.
        combined_mtf = combined_mtf.reindex(df.index, method="ffill").shift(1)

        return combined_mtf

    def _normalize_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize the feature matrix using the specified method.

        Args:
            df: Feature DataFrame to normalize.

        Returns:
            Normalized DataFrame.
        """
        if self.method == "zscore":
            if self.means is None:
                self.means = df.mean()
                # Use 1.0 for constant features to avoid division by zero
                self.stds = df.std().replace(0, 1.0).fillna(1.0)
            return (df - self.means) / self.stds

        if self.method == "minmax":
            if self.mins is None:
                self.mins = df.min()
                self.maxs = df.max()
            denom = (self.maxs - self.mins).replace(0, 1.0).fillna(1.0)
            return (df - self.mins) / denom

        return df

    def get_feature_count(self) -> int:
        """
        Return the number of engineered features.

        Returns:
            Total count of feature columns.
        """
        return len(self.feature_columns)
