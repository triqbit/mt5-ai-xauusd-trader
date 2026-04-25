"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/feature_engineering.py
Compute 140+ technical features from raw OHLCV data using TA-Lib.
Includes multi-timeframe features, candle patterns, and volume profile.
"""

import logging
from typing import List, Optional

import numpy as np
import pandas as pd
import talib
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Enterprise-grade feature engineering engine.
    Computes technical indicators, candle patterns, and multi-timeframe features.
    """

    def __init__(self, timeframes: Optional[List[str]] = None):
        """
        Initialize FeatureEngineer.

        Args:
            timeframes: List of timeframes to compute features for.
                        Defaults to ['M1', 'M5', 'M15', 'H1', 'H4', 'D1'].
        """
        self.timeframes = timeframes or ["M1", "M5", "M15", "H1", "H4", "D1"]
        self.scaler = StandardScaler()
        self._is_fitted = False

    def extract_features(self, df: pd.DataFrame, fit_scaler: bool = True) -> pd.DataFrame:
        """
        Main entry point for feature extraction.

        Args:
            df: Input DataFrame with 'open', 'high', 'low', 'close', 'volume' columns.
            fit_scaler: Whether to fit the scaler on the data.

        Returns:
            DataFrame containing normalized features.
        """
        if df.empty:
            return pd.DataFrame()

        df = df.copy()
        df.columns = [c.lower() for c in df.columns]

        # Ensure 'time' is index if present
        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"])
            df.set_index("time", inplace=True)

        feature_dfs = []

        # Base timeframe features
        base_features = self._compute_base_features(df, prefix="base")
        feature_dfs.append(base_features)

        # Multi-timeframe features
        # Note: We assume input df is at the lowest timeframe (e.g., M1)
        # to allow resampling to higher timeframes.
        for tf in self.timeframes:
            if tf == "M1": # Assuming base is M1
                continue

            resampled_df = self._resample_data(df, tf)
            if resampled_df.empty:
                logger.warning("Resampled dataframe for %s is empty. Skipping.", tf)
                continue

            tf_features = self._compute_base_features(resampled_df, prefix=tf)

            # Shift features by one period to avoid look-ahead bias
            # Ensures that at time T, we only use the candle that completed BEFORE T.
            tf_features = tf_features.shift(1)

            # Reindex to match the original base timeframe
            tf_features = tf_features.reindex(df.index).ffill()
            feature_dfs.append(tf_features)

        # Combine all features
        full_df = pd.concat(feature_dfs, axis=1)

        # Drop columns that are entirely NaN (e.g. not enough data for large lookbacks on high TFs)
        full_df.dropna(axis=1, how="all", inplace=True)

        # Drop rows with NaNs (initial lookback periods)
        full_df.dropna(inplace=True)

        if full_df.empty:
            logger.error("Feature matrix is empty after dropping NaNs. Increase input data length.")
            return pd.DataFrame()

        # Normalize
        normalized_data = self._normalize(full_df, fit_scaler)

        return pd.DataFrame(normalized_data, index=full_df.index, columns=full_df.columns)

    def _compute_base_features(self, df: pd.DataFrame, prefix: str) -> pd.DataFrame:
        """Compute all indicators for a given dataframe and prefix."""
        features = pd.DataFrame(index=df.index)

        # TA-Lib expects double arrays
        close = df["close"].values.astype(float)
        high = df["high"].values.astype(float)
        low = df["low"].values.astype(float)
        open_ = df["open"].values.astype(float)
        volume = df["volume"].values.astype(float)

        # 1. EMA Stacks
        for period in [8, 21, 50, 200]:
            if len(close) >= period:
                features[f"{prefix}_ema_{period}"] = talib.EMA(close, timeperiod=period)

        # 2. RSI
        if len(close) >= 14:
            features[f"{prefix}_rsi"] = talib.RSI(close, timeperiod=14)

        # 3. MACD
        if len(close) >= 26:
            macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
            features[f"{prefix}_macd"] = macd
            features[f"{prefix}_macd_signal"] = macdsignal
            features[f"{prefix}_macd_hist"] = macdhist

        # 4. ATR
        if len(close) >= 14:
            features[f"{prefix}_atr"] = talib.ATR(high, low, close, timeperiod=14)

        # 5. Bollinger Bands
        if len(close) >= 20:
            upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
            features[f"{prefix}_bb_upper"] = upper
            features[f"{prefix}_bb_middle"] = middle
            features[f"{prefix}_bb_lower"] = lower

        # 6. Additional Momentum Indicators
        if len(close) >= 14:
            features[f"{prefix}_adx"] = talib.ADX(high, low, close, timeperiod=14)
            features[f"{prefix}_cci"] = talib.CCI(high, low, close, timeperiod=14)
        if len(close) >= 10:
            features[f"{prefix}_mom"] = talib.MOM(close, timeperiod=10)
            features[f"{prefix}_roc"] = talib.ROC(close, timeperiod=10)

        if len(close) >= 5:
            slowk, slowd = talib.STOCH(high, low, close)
            features[f"{prefix}_stoch_k"] = slowk
            features[f"{prefix}_stoch_d"] = slowd

        # 7. Volume Profile (Basic)
        features[f"{prefix}_obv"] = talib.OBV(close, volume)
        features[f"{prefix}_ad"] = talib.AD(high, low, close, volume)

        # 8. Candle Patterns (60+)
        pattern_functions = list(talib.get_function_groups()["Pattern Recognition"])
        for pattern in pattern_functions:
            features[f"{prefix}_{pattern.lower()}"] = getattr(talib, pattern)(open_, high, low, close)

        return features

    def _resample_data(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        Resample OHLCV data to a higher timeframe.

        Args:
            df: Base DataFrame.
            timeframe: Target timeframe (e.g., 'M5', 'H1').

        Returns:
            Resampled DataFrame.
        """
        logic = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }

        # Map timeframe strings to pandas freq
        tf_map = {
            "M5": "5min",
            "M15": "15min",
            "H1": "1h",
            "H4": "4h",
            "D1": "1D",
        }
        freq = tf_map.get(timeframe, "5min")
        return df.resample(freq).apply(logic).dropna()

    def _normalize(self, df: pd.DataFrame, fit_scaler: bool) -> np.ndarray:
        """Normalize the feature matrix."""
        if fit_scaler:
            return self.scaler.fit_transform(df)
        elif hasattr(self.scaler, "mean_"):
            return self.scaler.transform(df)
        else:
            logger.warning("Scaler not fitted. Returning unnormalized data.")
            return df.values
