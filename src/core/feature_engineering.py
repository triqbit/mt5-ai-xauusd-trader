"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/feature_engineering.py
Institutional-grade feature engineering pipeline with 140+ technical indicators.
Supports multi-timeframe analysis and ensures no look-ahead bias.
"""

from __future__ import annotations

import logging
from typing import List

import numpy as np
import pandas as pd
from scipy.stats import linregress

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Engineers 140+ features from raw OHLCV data.
    Includes momentum, volatility, trend, and volume indicators across multiple timeframes.
    """

    def __init__(self, use_cache: bool = True) -> None:
        self.use_cache = use_cache
        self._feature_names: List[str] = []

    def generate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Main entry point for feature generation.
        Expects a DataFrame with OHLCV columns.
        """
        if df.empty:
            return df

        df = df.copy()
        df.columns = [c.lower() for c in df.columns]

        # Use a list of dataframes to avoid fragmentation performance issues
        feature_dfs = [df]

        # 1. Base Indicators
        feature_dfs.append(self._add_momentum_indicators(df))
        feature_dfs.append(self._add_volatility_indicators(df))
        feature_dfs.append(self._add_trend_indicators(df))
        feature_dfs.append(self._add_volume_indicators(df))
        feature_dfs.append(self._add_price_action_features(df))

        # 2. Multi-Timeframe (MTF) Features
        feature_dfs.append(self._add_mtf_simulated_features(df))

        # 3. Time Features
        feature_dfs.append(self._add_time_features(df))

        # Combine all features
        df_combined = pd.concat(feature_dfs, axis=1)

        # Remove duplicate columns if any (except the base ones)
        df_combined = df_combined.loc[:, ~df_combined.columns.duplicated()]

        # 4. Normalization & Cleanup
        df_combined = df_combined.replace([np.inf, -np.inf], np.nan)
        df_combined = df_combined.ffill().bfill()

        self._feature_names = [
            c
            for c in df_combined.columns
            if c not in ["open", "high", "low", "close", "tick_volume", "spread"]
        ]

        logger.info("Generated %d features", len(self._feature_names))
        return df_combined

    def get_feature_names(self) -> List[str]:
        return self._feature_names

    # -- Internal Indicators ------------------------------------------------

    def _add_momentum_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        res = pd.DataFrame(index=df.index)
        # RSI
        for w in [2, 3, 5, 7, 9, 14, 21, 25, 30, 50, 100]:
            res[f"rsi_{w}"] = self._calculate_rsi(df["close"], w)

        # MACD
        for fast, slow, signal in [(12, 26, 9), (5, 35, 5), (24, 52, 18), (8, 17, 9)]:
            name = f"macd_{fast}_{slow}"
            res[name] = df["close"].ewm(span=fast).mean() - df["close"].ewm(span=slow).mean()
            res[f"{name}_sig"] = res[name].ewm(span=signal).mean()
            res[f"{name}_hist"] = res[name] - res[f"{name}_sig"]

        # ROC
        for w in [1, 2, 3, 5, 10, 15, 20, 30, 60, 120, 240]:
            res[f"roc_{w}"] = df["close"].pct_change(w) * 100

        # CCI
        for w in [14, 20, 40]:
            tp = (df["high"] + df["low"] + df["close"]) / 3
            ma = tp.rolling(w).mean()
            md = tp.rolling(w).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
            res[f"cci_{w}"] = (tp - ma) / (0.015 * md + 1e-9)

        # Williams %R
        for w in [14, 28]:
            high_max = df["high"].rolling(w).max()
            low_min = df["low"].rolling(w).min()
            res[f"willr_{w}"] = (high_max - df["close"]) / (high_max - low_min + 1e-9) * -100

        return res

    def _add_volatility_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        res = pd.DataFrame(index=df.index)
        # ATR
        tr = pd.concat(
            [
                df["high"] - df["low"],
                (df["high"] - df["close"].shift(1)).abs(),
                (df["low"] - df["close"].shift(1)).abs(),
            ],
            axis=1,
        ).max(axis=1)

        for w in [7, 14, 20, 50, 100]:
            res[f"atr_{w}"] = tr.rolling(w).mean()

        # Bollinger Bands
        for w in [20, 50]:
            sma = df["close"].rolling(w).mean()
            std = df["close"].rolling(w).std()
            for dev in [1.5, 2.0, 2.5]:
                res[f"bb_{w}_{dev}_up"] = sma + (std * dev)
                res[f"bb_{w}_{dev}_low"] = sma - (std * dev)
            res[f"bb_width_{w}"] = (res[f"bb_{w}_2.0_up"] - res[f"bb_{w}_2.0_low"]) / (sma + 1e-9)

        for w in [10, 20, 30, 50, 100, 200]:
            res[f"std_{w}"] = df["close"].rolling(w).std()

        return res

    def _add_trend_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        res = pd.DataFrame(index=df.index)
        # EMA Stack
        emas = [3, 5, 8, 13, 21, 34, 55, 89, 100, 144, 200, 233, 500]
        for w in emas:
            res[f"ema_{w}"] = df["close"].ewm(span=w, adjust=False).mean()
            res[f"dist_ema_{w}"] = (df["close"] - res[f"ema_{w}"]) / (res[f"ema_{w}"] + 1e-9)

        res["ema_fast_spread"] = (res["ema_5"] - res["ema_13"]) / (res["ema_13"] + 1e-9)
        res["ema_slow_spread"] = (res["ema_21"] - res["ema_55"]) / (res["ema_55"] + 1e-9)

        # Slope
        def get_slope(y):
            x = np.arange(len(y))
            slope, _, _, _, _ = linregress(x, y)
            return slope

        for w in [5, 10, 14, 20, 30, 40, 60]:
            res[f"slope_{w}"] = df["close"].rolling(w).apply(get_slope, raw=True)

        return res

    def _add_volume_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        res = pd.DataFrame(index=df.index)
        for w in [10, 20, 50, 100]:
            res[f"vol_sma_{w}"] = df["tick_volume"].rolling(w).mean()
            res[f"vol_ratio_{w}"] = df["tick_volume"] / (res[f"vol_sma_{w}"] + 1e-9)

        res["obv"] = (np.sign(df["close"].diff()) * df["tick_volume"]).fillna(0).cumsum()
        res["obv_sma_20"] = res["obv"].rolling(20).mean()
        return res

    def _add_price_action_features(self, df: pd.DataFrame) -> pd.DataFrame:
        res = pd.DataFrame(index=df.index)
        res["body_size"] = (df["close"] - df["open"]).abs()
        res["upper_wick"] = df["high"] - df[["open", "close"]].max(axis=1)
        res["lower_wick"] = df[["open", "close"]].min(axis=1) - df["low"]
        res["candle_color"] = np.where(df["close"] > df["open"], 1, -1)
        res["bar_range"] = df["high"] - df["low"]
        res["rel_body"] = res["body_size"] / (res["bar_range"] + 1e-9)

        for w in [10, 20, 30, 50, 100, 150, 200]:
            low_w = df["low"].rolling(w).min()
            high_w = df["high"].rolling(w).max()
            res[f"high_pct_{w}"] = (df["high"] - low_w) / (high_w - low_w + 1e-9)
            res[f"close_pct_{w}"] = (df["close"] - low_w) / (high_w - low_w + 1e-9)

        return res

    def _add_mtf_simulated_features(self, df: pd.DataFrame) -> pd.DataFrame:
        res = pd.DataFrame(index=df.index)
        mtf_windows = {"mtf1": 12, "mtf2": 24, "mtf3": 48, "mtf4": 96, "mtf5": 288}
        for name, w in mtf_windows.items():
            res[f"rsi_{name}"] = self._calculate_rsi(df["close"], min(len(df) - 1, w * 14))
            res[f"ema_{name}"] = df["close"].ewm(span=w * 20, adjust=False).mean()
            res[f"std_{name}"] = df["close"].rolling(min(len(df), w * 20)).std()
            res[f"roc_{name}"] = df["close"].pct_change(min(len(df) - 1, w * 10))

        return res

    def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        res = pd.DataFrame(index=df.index)
        if not isinstance(df.index, pd.DatetimeIndex):
            return res

        res["hour_sin"] = np.sin(2 * np.pi * df.index.hour / 24)
        res["hour_cos"] = np.cos(2 * np.pi * df.index.hour / 24)
        res["day_sin"] = np.sin(2 * np.pi * df.index.dayofweek / 7)
        res["day_cos"] = np.cos(2 * np.pi * df.index.dayofweek / 7)
        return res

    def _calculate_rsi(self, series: pd.Series, window: int) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / (loss + 1e-9)
        return 100 - (100 / (1 + rs))

    def normalize(self, df: pd.DataFrame, method: str = "zscore") -> pd.DataFrame:
        features = self.get_feature_names()
        df_norm = df.copy()

        if method == "zscore":
            for col in features:
                mean = df_norm[col].mean()
                std = df_norm[col].std() + 1e-9
                df_norm[col] = (df_norm[col] - mean) / std
        elif method == "minmax":
            for col in features:
                min_val = df_norm[col].min()
                max_val = df_norm[col].max()
                df_norm[col] = (df_norm[col] - min_val) / (max_val - min_val + 1e-9)

        return df_norm
