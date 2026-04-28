"""
Institutional-grade feature engineering for XAUUSD trading.

This module computes 140+ features from raw OHLCV data using TA-Lib,
including multi-timeframe indicators, candle patterns, and volume profile.
"""

from typing import List, Optional

import numpy as np
import pandas as pd
import talib


class FeatureEngineer:
    """
    Computes 140+ features from OHLCV data for institutional trading.

    Attributes:
        use_zscore (bool): Whether to apply Z-score normalization.
        feature_cols (List[str]): List of generated feature column names.
    """

    def __init__(self, use_zscore: bool = True) -> None:
        """
        Initialize the FeatureEngineer.

        Args:
            use_zscore: If True, normalize features using Z-score.
        """
        self.use_zscore = use_zscore
        self.feature_cols: List[str] = []

    def compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute all features from raw OHLCV data.

        Args:
            df: Input DataFrame with 'open', 'high', 'low', 'close', 'volume' columns.
                Expected to be in M1 timeframe.

        Returns:
            DataFrame with original OHLCV and 140+ computed features.
        """
        # Ensure column names are lowercase
        df = df.copy()
        df.columns = [col.lower() for col in df.columns]

        # Cast to float for TA-Lib compatibility
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)

        base_df = df.copy()

        # 1. Base timeframe features (M1)
        df = self._add_indicators(df, prefix="m1")

        # 2. Multi-timeframe features
        timeframes = {
            "5min": "m5",
            "15min": "m15",
            "1h": "h1",
            "4h": "h4",
            "1d": "d1",
        }

        for tf_freq, prefix in timeframes.items():
            tf_df = self._resample_and_compute(base_df, tf_freq, prefix)
            # Reindex to base M1 and forward fill
            tf_df = tf_df.reindex(base_df.index).ffill()
            df = pd.concat([df, tf_df], axis=1)

        # 3. Candle Patterns (on M1)
        df = self._add_candle_patterns(df)

        # 4. Volume Profile (on M1)
        df = self._add_volume_profile(df)

        # Drop columns that are entirely NaN (e.g., if history is too short for high TF indicators)
        df = df.dropna(axis=1, how="all")

        # Drop rows with NaNs from indicator warmup
        df = df.dropna()

        # Identify feature columns (excluding original OHLCV)
        self.feature_cols = [
            col
            for col in df.columns
            if col not in ["open", "high", "low", "close", "volume"]
        ]

        # 5. Normalization
        if self.use_zscore:
            df[self.feature_cols] = self._normalize(df[self.feature_cols])

        # Final check for any remaining NaNs or Infs
        df = df.replace([np.inf, -np.inf], np.nan).dropna()

        return df

    def _add_indicators(self, df: pd.DataFrame, prefix: str) -> pd.DataFrame:
        """Add TA-Lib indicators and EMA stacks."""
        if len(df) < 2:
            return df

        close = df["close"].values.astype(float)
        high = df["high"].values.astype(float)
        low = df["low"].values.astype(float)
        # volume = df["volume"].values.astype(float)

        # RSI
        df[f"{prefix}_rsi"] = talib.RSI(close, timeperiod=14)

        # MACD
        macd, macdsignal, macdhist = talib.MACD(
            close, fastperiod=12, slowperiod=26, signalperiod=9
        )
        df[f"{prefix}_macd"] = macd
        df[f"{prefix}_macd_signal"] = macdsignal
        df[f"{prefix}_macd_hist"] = macdhist

        # ATR
        df[f"{prefix}_atr"] = talib.ATR(high, low, close, timeperiod=14)

        # Bollinger Bands
        upper, middle, lower = talib.BBANDS(close, timeperiod=20)
        df[f"{prefix}_bb_upper"] = upper
        df[f"{prefix}_bb_middle"] = middle
        df[f"{prefix}_bb_lower"] = lower
        df[f"{prefix}_bb_width"] = (upper - lower) / (middle + 1e-9)

        # EMA Stacks - Adjusted for higher timeframes to avoid massive warmup
        ema_periods = [8, 21, 50]
        if prefix in ["m1", "m5", "m15", "h1"]:
            ema_periods.append(200)

        for p in ema_periods:
            ema = talib.EMA(close, timeperiod=p)
            df[f"{prefix}_ema_{p}"] = ema
            df[f"{prefix}_dist_ema_{p}"] = (close - ema) / (ema + 1e-9)

        # Price Momentum
        df[f"{prefix}_mom"] = talib.MOM(close, timeperiod=10)
        df[f"{prefix}_roc"] = talib.ROC(close, timeperiod=10)

        # ADX
        df[f"{prefix}_adx"] = talib.ADX(high, low, close, timeperiod=14)

        return df

    def _resample_and_compute(
        self, df: pd.DataFrame, freq: str, prefix: str
    ) -> pd.DataFrame:
        """Resample M1 data to a higher timeframe and compute features."""
        resampled = df.resample(freq).agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        resampled = self._add_indicators(resampled, prefix=prefix)

        # Important: Shift by 1 to prevent look-ahead bias
        # The feature at time T must only use data from candles completed BEFORE T.
        feature_cols = [col for col in resampled.columns if col.startswith(prefix)]
        resampled[feature_cols] = resampled[feature_cols].shift(1)

        return resampled[feature_cols]

    def _add_candle_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add 60+ TA-Lib candle pattern recognition features."""
        op = df["open"].values
        hi = df["high"].values
        lo = df["low"].values
        cl = df["close"].values

        patterns = talib.get_function_groups()["Pattern Recognition"]
        for pattern in patterns:
            pattern_func = getattr(talib, pattern)
            df[f"pattern_{pattern.lower()}"] = pattern_func(op, hi, lo, cl)

        return df

    def _add_volume_profile(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based features."""
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        volume = df["volume"].values

        # On-Balance Volume
        df["vol_obv"] = talib.OBV(close, volume)

        # Chaikin A/D Line
        df["vol_ad"] = talib.AD(high, low, close, volume)

        # Chaikin Oscillator
        df["vol_adosc"] = talib.ADOSC(high, low, close, volume)

        # Relative Volume (Vol / MA(Vol, 20))
        vol_ma20 = talib.MA(volume, timeperiod=20)
        df["vol_rel"] = volume / vol_ma20

        return df

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply Z-score normalization."""
        # Avoid division by zero
        std = df.std()
        std = std.replace(0, 1)
        return (df - df.mean()) / std
