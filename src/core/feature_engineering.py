"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/feature_engineering.py
Advanced feature engineering for XAUUSD trading.
Computes 140+ features including multi-timeframe indicators.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import pandas_ta as ta

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Enterprise-grade feature engineering engine.
    Calculates technical indicators, candle patterns, and multi-timeframe features.
    """

    def __init__(self) -> None:
        pass

    def compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute 140+ features from OHLCV data.

        Args:
            df: DataFrame with 'open', 'high', 'low', 'close', 'tick_volume' columns.
                Index should be DatetimeIndex.

        Returns:
            DataFrame with original columns plus 140+ features.
        """
        if df.empty:
            return df

        # Avoid side effects by copying
        df = df.copy()

        # Ensure column names are lowercase
        df.columns = [c.lower() for c in df.columns]
        if "tick_volume" in df.columns and "volume" not in df.columns:
            df["volume"] = df["tick_volume"]

        # 1. Basic Lags and Returns
        for lag in [1, 2, 3, 5]:
            df[f"return_{lag}"] = df["close"].pct_change(lag)
            df[f"log_return_{lag}"] = np.log(df["close"] / df["close"].shift(lag))

        # 2. EMA Stacks (8, 21, 50, 200)
        for period in [8, 21, 50, 200]:
            df[f"ema_{period}"] = ta.ema(df["close"], length=period)
            df[f"dist_ema_{period}"] = (df["close"] - df[f"ema_{period}"]) / (
                df[f"ema_{period}"] + 1e-8
            )

        # 3. Standard Momentum & Volatility Indicators
        df.ta.rsi(length=14, append=True)
        df.ta.rsi(length=7, append=True)
        df.ta.rsi(length=21, append=True)

        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.atr(length=14, append=True)
        df.ta.bbands(length=20, std=2, append=True)
        df.ta.kc(length=20, scalar=2, append=True)

        df.ta.adx(length=14, append=True)
        df.ta.stoch(k=14, d=3, smooth_k=3, append=True)
        df.ta.cci(length=14, append=True)
        df.ta.willr(length=14, append=True)
        df.ta.mfi(length=14, append=True)
        df.ta.obv(append=True)
        df.ta.roc(length=10, append=True)
        df.ta.mom(length=10, append=True)

        # 4. Additional Indicators to reach 140+
        df.ta.aroon(length=25, append=True)
        df.ta.cmf(length=20, append=True)
        df.ta.cmo(length=14, append=True)
        df.ta.donchian(lower_length=20, upper_length=20, append=True)
        df.ta.fisher(length=9, append=True)
        df.ta.ichimoku(append=True)
        df.ta.kst(append=True)
        df.ta.ppo(append=True)
        df.ta.pvt(append=True)
        df.ta.rvi(length=14, append=True)
        df.ta.trix(length=18, append=True)
        df.ta.tsi(append=True)
        df.ta.uo(append=True)
        df.ta.vortex(length=14, append=True)

        # 4b. More indicators
        df.ta.alligator(append=True)
        df.ta.supertrend(append=True)
        df.ta.squeeze(append=True)
        df.ta.psar(append=True)
        df.ta.pdist(append=True)
        df.ta.massi(append=True)
        df.ta.linreg(append=True)
        df.ta.hwc(append=True)
        df.ta.ebsw(append=True)
        df.ta.dpo(append=True)
        df.ta.coppock(append=True)
        df.ta.chop(append=True)
        df.ta.accbands(append=True)
        df.ta.natr(append=True)
        df.ta.true_range(append=True)
        df.ta.alma(append=True)
        df.ta.aobv(append=True)
        df.ta.bop(append=True)
        df.ta.er(append=True)
        df.ta.efi(append=True)
        df.ta.kvo(append=True)
        df.ta.pgo(append=True)
        df.ta.qqe(append=True)
        df.ta.stc(append=True)
        df.ta.vidya(append=True)
        df.ta.zscore(append=True)
        df.ta.aberration(append=True)
        df.ta.ao(append=True)
        df.ta.amat(append=True)
        df.ta.bias(append=True)
        df.ta.brar(append=True)
        df.ta.cti(append=True)
        df.ta.decay(append=True)
        df.ta.increasing(append=True)
        df.ta.decreasing(append=True)

        # 5. Multi-Timeframe Features (Fixed Lookahead Bias)
        # M5, M15, H1, H4, D1
        tfs = {"5min": "5m", "15min": "15m", "1h": "1h", "4h": "4h", "1D": "1d"}
        for tf_freq, tf_label in tfs.items():
            try:
                resampled = df.resample(tf_freq).agg(
                    {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
                )
                # Compute indicators on resampled data
                resampled[f"rsi_14_{tf_label}"] = ta.rsi(resampled["close"], length=14)
                resampled[f"ema_21_{tf_label}"] = ta.ema(resampled["close"], length=21)
                resampled[f"atr_14_{tf_label}"] = ta.atr(
                    resampled["high"], resampled["low"], resampled["close"], length=14
                )

                # IMPORTANT: Shift resampled data to avoid LOOKAHEAD BIAS
                # A bar at 10:00 (1H TF) covers 10:00 to 10:59.
                # It can only be used at 11:00 or later.
                resampled_shifted = resampled[
                    [f"rsi_14_{tf_label}", f"ema_21_{tf_label}", f"atr_14_{tf_label}"]
                ].shift(1)

                # Join back using ffill to populate the intervals
                resampled_joined = resampled_shifted.reindex(df.index, method="ffill")
                df = pd.concat([df, resampled_joined], axis=1)
            except Exception as e:
                logger.warning("Resampling failed", tf=tf_freq, error=str(e))

        # 6. Candle Pattern Recognition (Expanded)
        df["body_size"] = np.abs(df["close"] - df["open"])
        df["total_range"] = df["high"] - df["low"]
        df["upper_shadow"] = df["high"] - np.maximum(df["close"], df["open"])
        df["lower_shadow"] = np.minimum(df["close"], df["open"]) - df["low"]

        # 6a. Native patterns from pandas-ta that DON'T require TA-Lib (if any exist)
        # cdl_z is native
        df.ta.cdl_z(append=True)

        # 6b. Manually implement common patterns
        # Doji
        df["cdl_doji"] = (df["body_size"] <= df["total_range"] * 0.1).astype(int)
        # Hammer (Bullish)
        df["cdl_hammer"] = (
            (df["lower_shadow"] > df["body_size"] * 2)
            & (df["upper_shadow"] < df["body_size"] * 0.5)
        ).astype(int)
        # Shooting Star (Bearish)
        df["cdl_star"] = (
            (df["upper_shadow"] > df["body_size"] * 2)
            & (df["lower_shadow"] < df["body_size"] * 0.5)
        ).astype(int)
        # Engulfing
        df["cdl_engulfing"] = (
            (df["close"] > df["open"])
            & (df["open"].shift(1) > df["close"].shift(1))
            & (df["close"] > df["open"].shift(1))
            & (df["open"] < df["close"].shift(1))
        ).astype(int)
        # Marubozu
        df["cdl_marubozu"] = (df["body_size"] > df["total_range"] * 0.9).astype(int)

        # 7. Volume Profile Proxy
        # VPVR usually shows volume at price. For a 1D matrix, we use Price-Volume interaction.
        df["pvol"] = df["close"] * df["volume"]
        df["vwap_dist"] = (
            df["close"] - ta.vwap(df["high"], df["low"], df["close"], df["volume"])
        ) / df["close"]
        # Rolling Value Area proxy: Price distance from volume-weighted mean
        window_vp = 20
        df["vol_weighted_mean"] = (df["pvol"].rolling(window_vp).sum()) / (
            df["volume"].rolling(window_vp).sum() + 1e-8
        )
        df["vp_dist"] = (df["close"] - df["vol_weighted_mean"]) / (df["vol_weighted_mean"] + 1e-8)

        # 8. Final touches
        logger.info("Features computed | count=%d", len(df.columns))
        return df

    def normalize_features(self, df: pd.DataFrame, window: int = 30) -> pd.DataFrame:
        """
        Normalize features using window-based Z-score.

        Args:
            df: Feature DataFrame.
            window: Rolling window size for normalization.

        Returns:
            Normalized DataFrame.
        """
        normalized_df = df.copy()

        # Identification of columns to normalize (exclude binary and price)
        # We also keep volume but normalize it.
        skip_cols = [
            "open",
            "high",
            "low",
            "close",
            "tick_volume",
            "volume",
            "total_range",
            "body_size",
            "upper_shadow",
            "lower_shadow",
        ]

        for col in df.columns:
            # Skip binary columns (candle patterns)
            if df[col].nunique() <= 2:
                continue

            if col in skip_cols:
                continue

            rolling = df[col].rolling(window=window)
            mean = rolling.mean()
            std = rolling.std()

            normalized_df[col] = (df[col] - mean) / (std + 1e-8)

        # Return with NaNs filled with 0 for safety in inference
        return normalized_df.fillna(0)


def get_feature_engineer() -> FeatureEngineer:
    """Returns a singleton instance of FeatureEngineer."""
    return FeatureEngineer()
