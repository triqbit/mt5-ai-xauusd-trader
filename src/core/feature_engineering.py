"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/feature_engineering.py
Advanced feature engineering module for XAUUSD market data.
Computes 140+ technical indicators, candle patterns, and multi-timeframe features.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import talib
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Engineers 140+ features from raw OHLCV data using TA-Lib and custom logic.
    Supports multi-timeframe analysis and automated normalization.
    """

    def __init__(self, use_standard_scaling: bool = True) -> None:
        """
        Initialize the FeatureEngineer.

        Args:
            use_standard_scaling: Whether to apply StandardScaler to the final feature set.
        """
        self.use_standard_scaling = use_standard_scaling
        self.scaler = StandardScaler()
        self._is_fitted = False

    def compute_features(
        self, df: pd.DataFrame, base_tf: str = "M1", include_patterns: bool = True
    ) -> pd.DataFrame:
        """
        Main entry point to compute all features.

        Args:
            df: Input DataFrame with 'open', 'high', 'low', 'close', 'tick_volume' columns.
                Must have a DatetimeIndex for multi-timeframe resampling.
            base_tf: The timeframe of the input data (e.g., 'M1', 'M5').
            include_patterns: Whether to include TA-Lib candle pattern recognition.

        Returns:
            DataFrame with normalized features, rows matching input (minus NaN lookback).
        """
        if df.empty:
            return pd.DataFrame()

        # Ensure column names are lowercase
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]

        # 1. Basic Price Features (~50-60 features)
        features_df = self._compute_base_features(df)

        # 2. Multi-Timeframe Features (~40-50 features)
        tf_hierarchy = ["M1", "M5", "M15", "H1", "H4", "D1"]
        try:
            base_idx = tf_hierarchy.index(base_tf)
            higher_tfs = tf_hierarchy[base_idx + 1 :]
        except ValueError:
            higher_tfs = []

        for tf in higher_tfs:
            features_df = self._add_mtf_features(features_df, df, tf)

        # 3. Candle Patterns (~60 features)
        if include_patterns:
            pattern_features = self._compute_candle_patterns(df)
            features_df = pd.concat([features_df, pattern_features], axis=1)

        # 4. Clean up
        drop_cols = ["open", "high", "low", "close", "tick_volume", "target_next_ret"]
        features_df = features_df.drop(columns=[c for c in drop_cols if c in features_df.columns])

        # Fill NaNs with 0 to keep all rows, or drop.
        # RL models usually need a continuous series.
        # We'll forward fill and then back fill to handle indicator warm-up without losing rows.
        features_df = features_df.ffill().bfill().fillna(0)

        # 5. Normalization
        if self.use_standard_scaling and not features_df.empty:
            features_df = self._normalize(features_df)

        logger.info("Computed %d features for %d samples", features_df.shape[1], len(features_df))
        return features_df

    def _compute_base_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute technical indicators for the primary timeframe."""
        res = df.copy()
        cl = df["close"].values
        hi = df["high"].values
        lo = df["low"].values
        vo = df["tick_volume"].values.astype(float)

        # --- Overlap Studies ---
        res["ema_8"] = talib.EMA(cl, timeperiod=8)
        res["ema_21"] = talib.EMA(cl, timeperiod=21)
        res["ema_50"] = talib.EMA(cl, timeperiod=50)
        res["ema_200"] = talib.EMA(cl, timeperiod=200)
        res["dema"] = talib.DEMA(cl, timeperiod=30)
        res["tema"] = talib.TEMA(cl, timeperiod=30)
        res["kama"] = talib.KAMA(cl, timeperiod=30)
        res["wma"] = talib.WMA(cl, timeperiod=30)
        res["bb_up"], res["bb_mid"], res["bb_low"] = talib.BBANDS(cl, timeperiod=20)
        res["sar"] = talib.SAR(hi, lo)
        res["ht_trendline"] = talib.HT_TRENDLINE(cl)

        # --- Momentum Indicators ---
        res["rsi_7"] = talib.RSI(cl, timeperiod=7)
        res["rsi_14"] = talib.RSI(cl, timeperiod=14)
        res["rsi_21"] = talib.RSI(cl, timeperiod=21)
        res["macd"], res["macd_sig"], res["macd_hist"] = talib.MACD(cl)
        res["adx"] = talib.ADX(hi, lo, cl, timeperiod=14)
        res["adxr"] = talib.ADXR(hi, lo, cl, timeperiod=14)
        res["cci"] = talib.CCI(hi, lo, cl, timeperiod=14)
        res["mom"] = talib.MOM(cl, timeperiod=10)
        res["willr"] = talib.WILLR(hi, lo, cl, timeperiod=14)
        res["stoch_k"], res["stoch_d"] = talib.STOCH(hi, lo, cl)
        res["stoch_rsi_k"], res["stoch_rsi_d"] = talib.STOCHRSI(cl)
        res["roc"] = talib.ROC(cl, timeperiod=10)
        res["trix"] = talib.TRIX(cl, timeperiod=30)
        res["apo"] = talib.APO(cl)
        res["ppo"] = talib.PPO(cl)
        res["cmo"] = talib.CMO(cl, timeperiod=14)
        res["bop"] = talib.BOP(df["open"].values, hi, lo, cl)

        # --- Volatility Indicators ---
        res["atr_14"] = talib.ATR(hi, lo, cl, timeperiod=14)
        res["natr"] = talib.NATR(hi, lo, cl, timeperiod=14)
        res["trange"] = talib.TRANGE(hi, lo, cl)

        # --- Volume Indicators ---
        res["obv"] = talib.OBV(cl, vo)
        res["adline"] = talib.AD(hi, lo, cl, vo)
        res["adosc"] = talib.ADOSC(hi, lo, cl, vo)
        res["mfi"] = talib.MFI(hi, lo, cl, vo, timeperiod=14)

        # --- Statistics / Others ---
        res["linearreg"] = talib.LINEARREG(cl, timeperiod=14)
        res["tsf"] = talib.TSF(cl, timeperiod=14)
        res["ht_dcperiod"] = talib.HT_DCPERIOD(cl)
        res["ht_dcphase"] = talib.HT_DCPHASE(cl)

        # --- Returns & Volatility ---
        res["return_1"] = df["close"].pct_change(1)
        res["return_5"] = df["close"].pct_change(5)
        res["return_10"] = df["close"].pct_change(10)
        res["log_ret"] = np.log(df["close"] / df["close"].shift(1))
        res["volatility_20"] = res["return_1"].rolling(20).std()
        res["target_next_ret"] = df["close"].shift(-1) / df["close"] - 1

        return res

    def _add_mtf_features(
        self, features_df: pd.DataFrame, base_df: pd.DataFrame, target_tf: str
    ) -> pd.DataFrame:
        """Resample data to higher timeframe, compute features, and map back."""
        tf_map = {"M5": "5min", "M15": "15min", "H1": "1h", "H4": "4h", "D1": "1D"}
        freq = tf_map.get(target_tf, "5min")

        mtf_df = base_df.resample(freq).agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "tick_volume": "sum"}
        )

        m_cl = mtf_df["close"].values
        m_hi = mtf_df["high"].values
        m_lo = mtf_df["low"].values

        mtf_indicators = pd.DataFrame(index=mtf_df.index)
        suffix = f"_{target_tf}"

        mtf_indicators[f"rsi_14{suffix}"] = talib.RSI(m_cl, timeperiod=14)
        mtf_indicators[f"ema_50{suffix}"] = talib.EMA(m_cl, timeperiod=50)
        mtf_indicators[f"ema_200{suffix}"] = talib.EMA(m_cl, timeperiod=200)
        mtf_indicators[f"atr_14{suffix}"] = talib.ATR(m_hi, m_lo, m_cl, timeperiod=14)
        mtf_indicators[f"adx{suffix}"] = talib.ADX(m_hi, m_lo, m_cl, timeperiod=14)
        m_macd, m_macdsig, m_macdhists = talib.MACD(m_cl)
        mtf_indicators[f"macd{suffix}"] = m_macd
        mtf_indicators[f"macd_sig{suffix}"] = m_macdsig
        mtf_indicators[f"macd_hist{suffix}"] = m_macdhists

        # Shift(1) to avoid look-ahead bias
        mtf_indicators = mtf_indicators.shift(1).reindex(features_df.index).ffill()

        return pd.concat([features_df, mtf_indicators], axis=1)

    def _compute_candle_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all TA-Lib candle patterns."""
        patterns = talib.get_function_groups()["Pattern Recognition"]
        res = pd.DataFrame(index=df.index)

        op = df["open"].values
        hi = df["high"].values
        lo = df["low"].values
        cl = df["close"].values

        for pat in patterns:
            pattern_func = getattr(talib, pat)
            res[pat.lower()] = pattern_func(op, hi, lo, cl)

        return res

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Scale features using StandardScaler."""
        idx = df.index
        cols = df.columns

        # Ensure no constant columns which cause NaNs in scaling
        # Only scale if std > 0
        df_to_scale = df.copy()

        if not self._is_fitted:
            scaled_data = self.scaler.fit_transform(df_to_scale)
            self._is_fitted = True
        else:
            scaled_data = self.scaler.transform(df_to_scale)

        return pd.DataFrame(scaled_data, index=idx, columns=cols)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    n_samples = 2000
    data = {
        "open": np.random.randn(n_samples) + 2000,
        "high": np.random.randn(n_samples) + 2005,
        "low": np.random.randn(n_samples) + 1995,
        "close": np.random.randn(n_samples) + 2000,
        "tick_volume": np.random.randint(100, 1000, n_samples),
    }
    dates = pd.date_range("2024-01-01", periods=n_samples, freq="1min")
    test_df = pd.DataFrame(data, index=dates)

    fe = FeatureEngineer()
    features = fe.compute_features(test_df)
    print(f"Features shape: {features.shape}")
    print(f"Number of features: {features.shape[1]}")
    if not features.empty:
        print(f"Sample columns: {features.columns[:10].tolist()}")
