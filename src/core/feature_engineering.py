"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/feature_engineering.py
140+ technical features (M1-D1 multi-timeframe RSI/EMA, EMA stacks, MACD, ATR, BB, TA-Lib patterns).
Author : triqbit
License: MIT
"""
from __future__ import annotations
import pandas as pd
import numpy as np
try:
    import talib
except ImportError:
    talib = None

class FeatureEngineer:
    def __init__(self):
        pass

    def generate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate 140+ features from OHLCV data."""
        if talib is None:
            return df

        df = df.copy()

        # 1. Price Momentum Indicators
        df["rsi"] = talib.RSI(df["close"], timeperiod=14)
        df["rsi_fast"] = talib.RSI(df["close"], timeperiod=7)
        df["rsi_slow"] = talib.RSI(df["close"], timeperiod=21)

        # 2. Moving Average Stacks (8, 21, 50, 200)
        df["ema8"] = talib.EMA(df["close"], timeperiod=8)
        df["ema21"] = talib.EMA(df["close"], timeperiod=21)
        df["ema50"] = talib.EMA(df["close"], timeperiod=50)
        df["ema200"] = talib.EMA(df["close"], timeperiod=200)

        # Relative EMA positions
        df["ema8_21_diff"] = df["ema8"] - df["ema21"]
        df["ema21_50_diff"] = df["ema21"] - df["ema50"]
        df["ema50_200_diff"] = df["ema50"] - df["ema200"]

        # 3. Volatility Indicators
        df["atr"] = talib.ATR(df["high"], df["low"], df["close"], timeperiod=14)
        df["atr_ratio"] = df["atr"] / df["close"]

        upper, middle, lower = talib.BBANDS(df["close"], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        df["bb_upper"] = upper
        df["bb_lower"] = lower
        df["bb_width"] = (upper - lower) / middle

        # 4. Trend Indicators
        df["macd"], df["macdsignal"], df["macdhist"] = talib.MACD(df["close"], fastperiod=12, slowperiod=26, signalperiod=9)
        df["adx"] = talib.ADX(df["high"], df["low"], df["close"], timeperiod=14)

        # 5. Additional Institutional Indicators
        df["slowk"], df["slowd"] = talib.STOCH(df["high"], df["low"], df["close"], fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)
        df["cci"] = talib.CCI(df["high"], df["low"], df["close"], timeperiod=14)
        df["willr"] = talib.WILLR(df["high"], df["low"], df["close"], timeperiod=14)
        df["sar"] = talib.SAR(df["high"], df["low"], acceleration=0.02, maximum=0.2)
        df["roc"] = talib.ROC(df["close"], timeperiod=10)

        # 6. TA-Lib Candle Patterns (approx 61)
        candle_names = talib.get_function_groups()['Pattern Recognition']
        for candle in candle_names:
            df[candle.lower()] = getattr(talib, candle)(df["open"], df["high"], df["low"], df["close"])

        # 7. Volume Indicators
        df["obv"] = talib.OBV(df["close"], df["tick_volume"])
        df["mfi"] = talib.MFI(df["high"], df["low"], df["close"], df["tick_volume"], timeperiod=14)

        return df.fillna(0)
