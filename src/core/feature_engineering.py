"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/feature_engineering.py
Advanced feature engineering for XAUUSD trading using TA-Lib.
Provides 140+ features including MTF, indicators, and candle patterns.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np
import pandas as pd
import talib

logger = logging.getLogger(__name__)

class FeatureEngineer:
    """
    Advanced Feature Engineering class for generating technical indicators
    and candle patterns from OHLCV data.
    """

    def __init__(self, base_timeframe: str = "M5",
                 target_timeframes: List[str] = ["M15", "H1"]):
        """
        Initialize FeatureEngineer.

        Args:
            base_timeframe: The timeframe of the input data.
            target_timeframes: List of higher timeframes for MTF analysis.
        """
        self.base_timeframe = base_timeframe
        self.target_timeframes = target_timeframes
        self.feature_names: List[str] = []

    def compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute all features for the given OHLCV DataFrame.

        Args:
            df: Input DataFrame with columns ['open', 'high', 'low', 'close', 'tick_volume'].

        Returns:
            DataFrame with original data and 140+ features, normalized.
        """
        # Ensure column names are lowercase
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]

        # Check for required columns
        required = ["open", "high", "low", "close", "tick_volume"]
        if not all(col in df.columns for col in required):
            raise ValueError(f"DataFrame must contain {required} columns")

        # 1. Base technical indicators
        df = self._add_indicators(df)

        # 2. Multi-timeframe features
        df = self._add_mtf_features(df)

        # 3. Candle patterns
        df = self._add_candle_patterns(df)

        # 4. Volume profile features
        df = self._add_volume_features(df)

        # 5. Normalization
        df = self._normalize(df)

        # 6. Final cleanup - ensure column names are consistent and drop NaNs
        df.columns = [c.lower() for c in df.columns]
        df = df.dropna()

        self.feature_names = [c for c in df.columns if c not in required]
        logger.info(f"Generated {len(self.feature_names)} features.")

        return df

    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add core technical indicators."""
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values

        # EMA Stacks
        for p in [8, 13, 21, 34, 50, 89, 144, 200]:
            df[f"ema{p}"] = talib.EMA(close, timeperiod=p)
            # Distance from EMA
            df[f"dist_ema{p}"] = (df["close"] - df[f"ema{p}"]) / (df[f"ema{p}"] + 1e-8)

        # SMA Stacks
        for p in [20, 50, 100, 200]:
            df[f"sma{p}"] = talib.SMA(close, timeperiod=p)

        # RSI
        for p in [7, 14, 21, 28]:
            df[f"rsi_{p}"] = talib.RSI(close, timeperiod=p)

        # MACD
        macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        df["macd"] = macd
        df["macd_signal"] = macdsignal
        df["macd_hist"] = macdhist

        # ATR
        for p in [7, 14, 21]:
            df[f"atr_{p}"] = talib.ATR(high, low, close, timeperiod=p)
            df[f"atr_pct_{p}"] = df[f"atr_{p}"] / (df["close"] + 1e-8)

        # Bollinger Bands
        for p in [10, 20, 50]:
            upper, middle, lower = talib.BBANDS(close, timeperiod=p, nbdevup=2, nbdevdn=2, matype=0)
            df[f"bb_upper_{p}"] = upper
            df[f"bb_middle_{p}"] = middle
            df[f"bb_lower_{p}"] = lower
            df[f"bb_width_{p}"] = (upper - lower) / (middle + 1e-8)
            df[f"bb_pct_{p}"] = (df["close"] - lower) / (upper - lower + 1e-8)

        # Momentum
        df["mom"] = talib.MOM(close, timeperiod=10)
        df["roc"] = talib.ROC(close, timeperiod=10)

        # ADX
        df["adx"] = talib.ADX(high, low, close, timeperiod=14)
        df["plus_di"] = talib.PLUS_DI(high, low, close, timeperiod=14)
        df["minus_di"] = talib.MINUS_DI(high, low, close, timeperiod=14)

        # Stochastic
        slowk, slowd = talib.STOCH(high, low, close, fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)
        df["stoch_k"] = slowk
        df["stoch_d"] = slowd

        # Additional indicators
        df["cci"] = talib.CCI(high, low, close, timeperiod=14)
        df["willr"] = talib.WILLR(high, low, close, timeperiod=14)
        df["ultosc"] = talib.ULTOSC(high, low, close, timeperiod1=7, timeperiod2=14, timeperiod3=28)
        df["trix"] = talib.TRIX(close, timeperiod=30)
        df["obv"] = talib.OBV(close, df["tick_volume"].values.astype(float))

        # More overlaps
        df["sar"] = talib.SAR(high, low, acceleration=0.02, maximum=0.2)
        df["tema"] = talib.TEMA(close, timeperiod=30)
        df["dema"] = talib.DEMA(close, timeperiod=30)

        return df

    def _add_mtf_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add features from higher timeframes.

        Resamples the base data to higher timeframes, computes indicators,
        and merges back to the original index.
        """
        # Ensure index is datetime for resampling
        if not isinstance(df.index, pd.DatetimeIndex):
            # Try to convert if it's not a datetime index
            try:
                df.index = pd.to_datetime(df.index)
            except Exception:
                logger.warning("DataFrame index is not DatetimeIndex and conversion failed. Skipping MTF.")
                return df

        base_df = df.copy()

        # Map MT5-style timeframes to pandas frequency strings
        tf_map = {
            "M1": "1min", "M5": "5min", "M15": "15min", "M30": "30min",
            "H1": "1h", "H4": "4h", "D1": "1D", "W1": "1W"
        }

        # Also add M1 if we are M5 base to increase feature count
        tfs = list(self.target_timeframes)
        if self.base_timeframe == "M5" and "M1" not in tfs:
             # M1 can't be added easily if base is M5 as it's downsampling.
             # We can only upsample.
             pass

        for tf in tfs:
            if tf not in tf_map:
                continue

            freq = tf_map[tf]

            # Resample OHLCV
            resampled = base_df.resample(freq).agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "tick_volume": "sum"
            }).dropna()

            if len(resampled) < 20:
                continue

            # Compute more indicators on the resampled data
            resampled[f"rsi_{tf}"] = talib.RSI(resampled["close"], timeperiod=14)
            resampled[f"atr_{tf}"] = talib.ATR(resampled["high"], resampled["low"], resampled["close"], timeperiod=14)
            resampled[f"ema20_{tf}"] = talib.EMA(resampled["close"], timeperiod=20)
            resampled[f"macd_{tf}"], _, _ = talib.MACD(resampled["close"])
            resampled[f"adx_{tf}"] = talib.ADX(resampled["high"], resampled["low"], resampled["close"])

            # Merge back (ffill ensures higher TF values are available at lower TF steps)
            cols_to_merge = [f"rsi_{tf}", f"atr_{tf}", f"ema20_{tf}", f"macd_{tf}", f"adx_{tf}"]

            # Add distances for higher TF EMAs
            resampled[f"dist_ema20_{tf}"] = (resampled["close"] - resampled[f"ema20_{tf}"]) / (resampled[f"ema20_{tf}"] + 1e-8)
            cols_to_merge.append(f"dist_ema20_{tf}")

            # SHIFT BY 1 to avoid lookahead bias!
            # We only want to know the values of the PREVIOUSLY closed higher TF bar.
            resampled_subset = resampled[cols_to_merge].shift(1)

            df = df.join(resampled_subset, how="left").ffill()

        return df

    def _add_candle_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add TA-Lib candle pattern recognition features."""
        o = df["open"].values
        h = df["high"].values
        l = df["low"].values
        c = df["close"].values

        pattern_funcs = talib.get_function_groups()["Pattern Recognition"]
        for func_name in pattern_funcs:
            # Pattern functions in TA-Lib take (open, high, low, close)
            pattern_result = getattr(talib, func_name)(o, h, l, c)
            df[func_name.lower()] = pattern_result

        return df

    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based features."""
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        volume = df["tick_volume"].values.astype(float)

        # On Balance Volume (already added in indicators but re-ensuring)
        if "obv" not in df.columns:
            df["obv"] = talib.OBV(close, volume)

        # Chaikin A/D Line
        df["ad"] = talib.AD(high, low, close, volume)

        # Chaikin Oscillator
        df["adosc"] = talib.ADOSC(high, low, close, volume, fastperiod=3, slowperiod=10)

        # Money Flow Index
        df["mfi"] = talib.MFI(high, low, close, volume, timeperiod=14)

        # Volume change
        df["vol_roc"] = df["tick_volume"].pct_change(periods=5)

        return df

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize features using rolling Z-score."""
        # Features that should NOT be normalized (e.g. raw OHLCV if needed,
        # though usually we only return normalized features)
        excluded = ["open", "high", "low", "close", "tick_volume"]

        # Features to normalize
        features_to_norm = [c for c in df.columns if c not in excluded]

        # Apply rolling Z-score (window of 100 for normalization)
        window = 100
        for col in features_to_norm:
            # Skip candle patterns as they are categorical (-100, 0, 100)
            if col.startswith("cdl"):
                # Scale candle patterns to [-1, 0, 1]
                df[col] = df[col] / 100.0
                continue

            rolling_mean = df[col].rolling(window=window).mean()
            rolling_std = df[col].rolling(window=window).std()

            # If all values are NaN in the rolling window (e.g. at the beginning),
            # this will result in NaNs which we drop later.
            df[col] = (df[col] - rolling_mean) / (rolling_std + 1e-8)

        return df
