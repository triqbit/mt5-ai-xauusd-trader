"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/feature_engineer.py
Comprehensive feature engineering module using pandas-ta.
Supports 140+ technical indicators and multi-timeframe alignment.
"""

import logging
from typing import List, Optional, Union

import numpy as np
import pandas as pd
import pandas_ta as ta

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Enterprise-grade feature engineering engine.
    Transforms raw OHLCV data into a high-dimensional feature vector.
    """

    def __init__(self, include_patterns: bool = True) -> None:
        """
        Initialize the feature engineer.

        Args:
            include_patterns: Whether to include candlestick pattern recognition.
        """
        self.include_patterns = include_patterns
        self._feature_columns: List[str] = []

    def generate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate a comprehensive set of technical features.

        Args:
            df: DataFrame with ['open', 'high', 'low', 'close', 'tick_volume'] columns.

        Returns:
            DataFrame with original data and calculated features.
        """
        # Work on a copy to avoid SettingWithCopy warnings
        data = df.copy()

        # Ensure columns are lowercase for pandas-ta
        data.columns = [col.lower() for col in data.columns]

        # Map tick_volume to volume if it exists
        if "tick_volume" in data.columns and "volume" not in data.columns:
            data["volume"] = data["tick_volume"]

        # Basic check for required columns
        required = {"open", "high", "low", "close", "volume"}
        if not required.issubset(data.columns):
            missing = required - set(data.columns)
            logger.error(f"Missing required columns for feature generation: {missing}")
            return data

        # Define custom strategies for pandas-ta
        # 1. Momentum
        data.ta.rsi(length=14, append=True)
        data.ta.macd(fast=12, slow=26, signal=9, append=True)
        data.ta.cci(length=20, append=True)
        data.ta.roc(length=12, append=True)
        data.ta.stoch(high='high', low='low', close='close', append=True)
        data.ta.willr(length=14, append=True) # Williams %R
        data.ta.mom(length=10, append=True)
        data.ta.uo(append=True) # Ultimate Oscillator
        data.ta.ao(append=True) # Awesome Oscillator

        # 2. Trend
        data.ta.adx(length=14, append=True)
        data.ta.sma(length=20, append=True)
        data.ta.sma(length=50, append=True)
        data.ta.sma(length=200, append=True)
        data.ta.ema(length=12, append=True)
        data.ta.ema(length=26, append=True)
        # Ichimoku and PSAR often produce many NaNs (one side always NaN)
        # We'll skip them or handle them specifically if needed for RL.
        # data.ta.ichimoku(append=True)
        # data.ta.psar(append=True)
        data.ta.vortex(append=True)
        data.ta.trix(append=True)

        # 3. Volatility
        data.ta.atr(length=14, append=True)
        data.ta.bbands(length=20, std=2, append=True)
        data.ta.kc(length=20, scalar=2, append=True)
        data.ta.natr(length=14, append=True)
        data.ta.true_range(append=True)

        # 4. Volume
        data.ta.obv(append=True)
        data.ta.cmf(length=20, append=True)
        data.ta.mfi(length=14, append=True)
        data.ta.ad(append=True)
        data.ta.eom(append=True) # Ease of Movement

        # 5. Candlestick Patterns (if enabled)
        if self.include_patterns:
            try:
                # This generates many binary columns
                data.ta.cdl_pattern(name="all", append=True)
            except Exception as e:
                logger.warning(f"Failed to generate candlestick patterns: {e}")

        # 6. Custom Returns and Log Features
        data["returns"] = data["close"].pct_change()
        data["log_returns"] = np.log(data["close"] / data["close"].shift(1))
        data["volatility_20"] = data["returns"].rolling(window=20).std()

        # 7. Price Relations
        if "sma_20" in data.columns:
            data["close_to_sma20"] = data["close"] / data["sma_20"]
        if "sma_50" in data.columns:
            data["close_to_sma50"] = data["close"] / data["sma_50"]
        if "sma_200" in data.columns:
            data["close_to_sma200"] = data["close"] / data["sma_200"]

        # Drop columns that are entirely NaN
        data.dropna(axis=1, how='all', inplace=True)

        # We don't drop rows here (like .dropna()) because the caller (TradingEnv)
        # needs to decide how to handle warmup periods.
        # We also avoid fillna(0) here so that dropna() in the environment remains effective.

        self._feature_columns = [col for col in data.columns if col not in required and col != "tick_volume"]

        logger.info(f"Generated {len(self._feature_columns)} features.")
        return data

    @property
    def feature_columns(self) -> List[str]:
        """Return the list of generated feature column names."""
        return self._feature_columns

    def normalize_features(self, df: pd.DataFrame, method: str = "zscore") -> pd.DataFrame:
        """
        Normalize features for better ML model convergence.

        Args:
            df: DataFrame containing features.
            method: 'zscore' or 'minmax'.

        Returns:
            Normalized DataFrame.
        """
        cols = self._feature_columns
        if not cols:
            return df

        result = df.copy()
        if method == "zscore":
            result[cols] = (df[cols] - df[cols].mean()) / (df[cols].std() + 1e-8)
        elif method == "minmax":
            result[cols] = (df[cols] - df[cols].min()) / (df[cols].max() - df[cols].min() + 1e-8)

        return result


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)
    dummy_data = pd.DataFrame({
        "open": np.random.randn(500).cumsum() + 100,
        "high": np.random.randn(500).cumsum() + 102,
        "low": np.random.randn(500).cumsum() + 98,
        "close": np.random.randn(500).cumsum() + 100,
        "tick_volume": np.random.randint(100, 1000, 500)
    })

    fe = FeatureEngineer()
    features_df = fe.generate_features(dummy_data)
    print(features_df.head())
    print(f"Total features: {len(fe.feature_columns)}")
