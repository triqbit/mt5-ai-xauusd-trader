"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/feature_engineering.py
Feature engineering pipeline generating 140+ technical indicators and MTF features.
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
    Advanced feature engineering for XAUUSD trading.
    Generates 140+ features including technical indicators, multi-timeframe
    analysis, candle patterns, and volume profiles.
    """

    def __init__(self, target_timeframes: Optional[List[str]] = None):
        """
        Initialize the feature engineer.

        Args:
            target_timeframes: List of timeframes to generate features for.
                               Defaults to ['M1', 'M5', 'M15', 'H1', 'H4', 'D1'].
        """
        if target_timeframes is None:
            target_timeframes = ["M1", "M5", "M15", "H1", "H4", "D1"]
        self.target_timeframes = target_timeframes

    def generate_features(self, df: pd.DataFrame, normalize: bool = True) -> pd.DataFrame:
        """
        Main entry point to generate the full feature matrix.

        Args:
            df: Input DataFrame with DatetimeIndex and ['open', 'high', 'low', 'close', 'volume'] columns.
            normalize: Whether to apply rolling Z-score normalization.

        Returns:
            pd.DataFrame: Augmented feature matrix.
        """
        # Ensure column names are lowercase
        df = df.copy()
        df.columns = [col.lower() for col in df.columns]

        # 1. Base Technical Indicators
        df = self._add_technical_indicators(df)

        # 2. Candle Pattern Recognition
        df = self._add_candle_patterns(df)

        # 3. Multi-Timeframe Features
        df = self._add_mtf_features(df)

        # 4. Remove rows with NaNs (due to indicators/resampling)
        initial_rows = len(df)
        df = df.dropna()
        logger.info(f"Dropped {initial_rows - len(df)} rows containing NaNs.")

        # 5. Normalization
        if normalize:
            df = self._apply_normalization(df)

        return df

    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add core TA-Lib indicators (Momentum, Volatility, Trend, Volume)."""
        close = df["close"].values.astype(np.float64)
        high = df["high"].values.astype(np.float64)
        low = df["low"].values.astype(np.float64)
        volume = df["volume"].values.astype(np.float64)

        # Trend Indicators
        df["ema_8"] = talib.EMA(close, timeperiod=8)
        df["ema_21"] = talib.EMA(close, timeperiod=21)
        df["ema_50"] = talib.EMA(close, timeperiod=50)
        df["ema_200"] = talib.EMA(close, timeperiod=200)

        df["sma_20"] = talib.SMA(close, timeperiod=20)
        df["sma_50"] = talib.SMA(close, timeperiod=50)
        df["wma_20"] = talib.WMA(close, timeperiod=20)
        df["kama_30"] = talib.KAMA(close, timeperiod=30)

        df["adx"] = talib.ADX(high, low, close, timeperiod=14)
        df["adxr"] = talib.ADXR(high, low, close, timeperiod=14)
        df["cci"] = talib.CCI(high, low, close, timeperiod=14)
        df["dema"] = talib.DEMA(close, timeperiod=30)
        df["dx"] = talib.DX(high, low, close, timeperiod=14)
        df["minus_di"] = talib.MINUS_DI(high, low, close, timeperiod=14)
        df["minus_dm"] = talib.MINUS_DM(high, low, timeperiod=14)
        df["plus_di"] = talib.PLUS_DI(high, low, close, timeperiod=14)
        df["plus_dm"] = talib.PLUS_DM(high, low, timeperiod=14)
        df["tema"] = talib.TEMA(close, timeperiod=30)
        df["trima"] = talib.TRIMA(close, timeperiod=30)
        df["ht_trendline"] = talib.HT_TRENDLINE(close)
        df["mama"], df["fama"] = talib.MAMA(close)
        df["sar"] = talib.SAR(high, low)

        # Momentum Indicators
        df["rsi"] = talib.RSI(close, timeperiod=14)
        df["rsi_7"] = talib.RSI(close, timeperiod=7)
        df["rsi_21"] = talib.RSI(close, timeperiod=21)

        df["macd"], df["macdsignal"], df["macdhist"] = talib.MACD(close)
        df["mfi"] = talib.MFI(high, low, close, volume, timeperiod=14)
        df["mom"] = talib.MOM(close, timeperiod=10)
        df["roc"] = talib.ROC(close, timeperiod=10)
        df["rocp"] = talib.ROCP(close, timeperiod=10)
        df["rocr"] = talib.ROCR(close, timeperiod=10)
        df["rocr100"] = talib.ROCR100(close, timeperiod=10)
        df["willr"] = talib.WILLR(high, low, close, timeperiod=14)
        df["stoch_k"], df["stoch_d"] = talib.STOCH(high, low, close)
        df["stochf_k"], df["stochf_d"] = talib.STOCHF(high, low, close)
        df["stochrsi_k"], df["stochrsi_d"] = talib.STOCHRSI(close)
        df["apo"] = talib.APO(close)
        df["bop"] = talib.BOP(df["open"].values, high, low, close)
        df["ppo"] = talib.PPO(close)
        df["ultosc"] = talib.ULTOSC(high, low, close)
        df["cmo"] = talib.CMO(close, timeperiod=14)
        df["trix"] = talib.TRIX(close, timeperiod=30)

        # Volatility Indicators
        df["atr"] = talib.ATR(high, low, close, timeperiod=14)
        df["natr"] = talib.NATR(high, low, close, timeperiod=14)
        df["trange"] = talib.TRANGE(high, low, close)
        df["bb_upper"], df["bb_middle"], df["bb_lower"] = talib.BBANDS(close)
        df["ht_dcperiod"] = talib.HT_DCPERIOD(close)
        df["ht_dcphase"] = talib.HT_DCPHASE(close)
        df["ht_phasor_inphase"], df["ht_phasor_quadrature"] = talib.HT_PHASOR(close)
        df["ht_sine"], df["ht_leadsine"] = talib.HT_SINE(close)
        df["ht_trendmode"] = talib.HT_TRENDMODE(close)

        # Volume Indicators
        df["ad"] = talib.AD(high, low, close, volume)
        df["adosc"] = talib.ADOSC(high, low, close, volume)
        df["obv"] = talib.OBV(close, volume)

        # Statistical Indicators
        df["beta"] = talib.BETA(high, low, timeperiod=5)
        df["correl"] = talib.CORREL(high, low, timeperiod=30)
        df["linearreg"] = talib.LINEARREG(close, timeperiod=14)
        df["linearreg_angle"] = talib.LINEARREG_ANGLE(close, timeperiod=14)
        df["linearreg_intercept"] = talib.LINEARREG_INTERCEPT(close, timeperiod=14)
        df["linearreg_slope"] = talib.LINEARREG_SLOPE(close, timeperiod=14)
        df["stddev"] = talib.STDDEV(close, timeperiod=5)
        df["tsf"] = talib.TSF(close, timeperiod=14)
        df["var"] = talib.VAR(close, timeperiod=5)

        # Price Transformations
        df["avgprice"] = talib.AVGPRICE(df["open"].values, high, low, close)
        df["medprice"] = talib.MEDPRICE(high, low)
        df["typprice"] = talib.TYPPRICE(high, low, close)
        df["wclprice"] = talib.WCLPRICE(high, low, close)
        df["midprice"] = talib.MIDPRICE(high, low, timeperiod=14)
        df["midpoint"] = talib.MIDPOINT(close, timeperiod=14)

        return df

    def _add_candle_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add all TA-Lib candle pattern recognition features."""
        op = df["open"].values.astype(np.float64)
        hi = df["high"].values.astype(np.float64)
        lo = df["low"].values.astype(np.float64)
        cl = df["close"].values.astype(np.float64)

        # Get all CDL pattern functions from TA-Lib
        patterns = [func for func in talib.get_functions() if func.startswith("CDL")]

        pattern_results = {}
        for pattern in patterns:
            pattern_func = getattr(talib, pattern)
            pattern_results[pattern.lower()] = pattern_func(op, hi, lo, cl)

        # Concatenate all results at once to avoid PerformanceWarning
        pattern_df = pd.DataFrame(pattern_results, index=df.index)
        df = pd.concat([df, pattern_df], axis=1)

        return df

    def _add_mtf_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add features from multiple timeframes.
        Uses 1-bar shift to prevent look-ahead bias.
        """
        base_df = df.copy()

        # Define mapping for resampling
        tf_map = {
            "M1": "1min",
            "M5": "5min",
            "M15": "15min",
            "H1": "1h",
            "H4": "4h",
            "D1": "1D"
        }

        for tf in self.target_timeframes:
            if tf not in tf_map:
                continue

            resample_rule = tf_map[tf]

            # Resample OHLCV
            resampled = base_df[["open", "high", "low", "close", "volume"]].resample(resample_rule).agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum"
            }).dropna()

            if len(resampled) < 30:
                logger.warning(f"Not enough data for timeframe {tf}. Skipping.")
                continue

            # Calculate key indicators for this TF
            tf_lower = tf.lower()
            resampled[f"rsi_{tf_lower}"] = talib.RSI(resampled["close"].values.astype(np.float64), timeperiod=14)
            resampled[f"atr_{tf_lower}"] = talib.ATR(
                resampled["high"].values.astype(np.float64),
                resampled["low"].values.astype(np.float64),
                resampled["close"].values.astype(np.float64),
                timeperiod=14
            )
            resampled[f"ema_20_{tf_lower}"] = talib.EMA(resampled["close"].values.astype(np.float64), timeperiod=20)

            # Shift by 1 to avoid look-ahead bias
            resampled = resampled.shift(1)

            # Select features to merge (avoid merging OHLCV again)
            mtf_features = resampled[[f"rsi_{tf_lower}", f"atr_{tf_lower}", f"ema_20_{tf_lower}"]]

            # Merge back to base dataframe
            df = pd.merge_asof(df, mtf_features, left_index=True, right_index=True, direction="backward")

        return df

    def _apply_normalization(self, df: pd.DataFrame, window: int = 100) -> pd.DataFrame:
        """
        Apply rolling Z-score normalization.
        (x - rolling_mean) / (rolling_std + epsilon)
        """
        epsilon = 1e-8

        # We only normalize numerical columns that aren't already categorical (like candle patterns)
        # However, for simplicity in RL, often we normalize everything or keep patterns as is.
        # Here we'll normalize everything that isn't the index.

        # Exclude candle patterns from normalization if they are purely -100, 0, 100?
        # Actually, Z-score on them is also fine.

        rolling_mean = df.rolling(window=window).mean()
        rolling_std = df.rolling(window=window).std()

        df_norm = (df - rolling_mean) / (rolling_std + epsilon)

        # Fill NaNs created by rolling window
        df_norm = df_norm.fillna(0)

        return df_norm


if __name__ == "__main__":
    # Quick test
    import numpy as np
    logging.basicConfig(level=logging.INFO)

    # 40 days of M1 data to ensure enough D1 data
    dates = pd.date_range("2024-01-01", periods=60000, freq="1min")
    data = {
        "open": np.random.randn(60000).cumsum() + 2000,
        "high": np.random.randn(60000).cumsum() + 2005,
        "low": np.random.randn(60000).cumsum() + 1995,
        "close": np.random.randn(60000).cumsum() + 2000,
        "volume": np.random.randint(100, 1000, 60000)
    }
    sample_df = pd.DataFrame(data, index=dates)

    fe = FeatureEngineer()
    features = fe.generate_features(sample_df)
    print(f"Generated {len(features.columns)} features.")
    if not features.empty:
        print(features.tail())
    else:
        print("Final feature matrix is empty. Check dropna() or data length.")
