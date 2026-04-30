"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/regime_detector.py
Market state classification and regime detection module.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import Dict

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class RegimeType(str, Enum):
    """Enumeration of possible market regimes."""
    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE_BREAKOUT = "volatile_breakout"
    LOW_VOLATILITY_DRIFT = "low_volatility_drift"
    NEWS_SHOCK = "news_shock"
    MEAN_REVERSION = "mean_reversion"
    UNKNOWN = "unknown"


class MarketRegime(BaseModel):
    """Typed market regime object with confidence and transition metadata."""
    label: RegimeType
    confidence: float = Field(..., ge=0.0, le=1.0)
    transition_score: float = Field(0.0, description="Score indicating probability of regime shift")
    metadata: Dict[str, float] = Field(default_factory=dict)


class RegimeDetector:
    """
    Market state classifier using statistical features and rule-based logic.
    Identifies regimes like Trending, Ranging, Volatile Breakout, etc.
    """

    def __init__(self, window_size: int = 20):
        self.window_size = window_size

    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract statistical features for regime classification.
        Required columns: open, high, low, close, volume.
        """
        features = pd.DataFrame(index=df.index)

        # 1. Volatility (ATR-like and Rolling Std)
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift(1)).abs()
        low_close = (df["low"] - df["close"].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        features["atr"] = tr.rolling(window=self.window_size).mean()
        features["volatility"] = df["close"].pct_change().rolling(window=self.window_size).std()

        # 2. Trend & Momentum (Slopes & RSI-like)
        features["close_sma"] = df["close"].rolling(window=self.window_size).mean()
        features["slope"] = (df["close"] - features["close_sma"]) / features["close_sma"]

        # Linear regression slope over window
        def calculate_slope(y):
            if len(y) < self.window_size:
                return 0.0
            x = np.arange(len(y))
            slope, _ = np.polyfit(x, y, 1)
            return slope

        features["reg_slope"] = df["close"].rolling(window=self.window_size).apply(calculate_slope)

        # 3. Range metrics (Bollinger Band Width, ADX-like)
        std = df["close"].rolling(window=self.window_size).std()
        features["bb_width"] = (std * 4) / features["close_sma"]

        # Relative Volatility (Current ATR vs historical)
        features["rel_vol"] = features["atr"] / features["atr"].rolling(window=self.window_size * 5).mean()

        return features.fillna(0)

    def classify(self, df: pd.DataFrame) -> MarketRegime:
        """
        Classify the current market regime based on the latest bar.
        """
        if len(df) < self.window_size * 2:
            return MarketRegime(label=RegimeType.UNKNOWN, confidence=0.0)

        features = self.extract_features(df).iloc[-1]

        # Heuristics for regime detection
        # Use helper for classification
        regime = self._classify_from_features(features)
        regime.metadata = features.to_dict()

        # Calculate transition score by comparing with previous features
        prev_features = self.extract_features(df).iloc[-2]
        feat_delta = np.abs(features - prev_features).sum()
        regime.transition_score = min(feat_delta / (features.abs().sum() + 1e-9), 1.0)

        return regime

    def classify_unsupervised(self, df: pd.DataFrame, n_clusters: int = 4) -> pd.Series:
        """
        Experimental unsupervised regime discovery using KMeans.
        """
        features = self.extract_features(df).dropna()
        if len(features) < n_clusters:
            return pd.Series(index=df.index)

        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(features)

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
        clusters = kmeans.fit_predict(scaled_features)

        result = pd.Series(clusters, index=features.index)
        return result.reindex(df.index)

    def label_historical(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Label a historical OHLCV DataFrame with regimes.
        Returns the original DataFrame with 'regime_label' and 'regime_confidence' columns.
        """
        labels = []
        confidences = []
        transition_scores = []

        # Optimization: Pre-calculate features
        all_features = self.extract_features(df)

        # We start from window_size * 2 to have enough data for rel_vol historical mean
        start_idx = self.window_size * 5

        # Initialize with UNKNOWN
        labels = [RegimeType.UNKNOWN] * len(df)
        confidences = [0.0] * len(df)
        transition_scores = [0.0] * len(df)

        for i in range(start_idx, len(df)):
            # We use a sliding window view for classification if needed,
            # but current heuristics only need the latest feature row.
            # However, for transition score, we compare with previous
            current_feat = all_features.iloc[i]
            prev_feat = all_features.iloc[i-1]

            # Simple transition score based on feature delta
            feat_delta = np.abs(current_feat - prev_feat).sum()
            transition_score = min(feat_delta / (current_feat.abs().sum() + 1e-9), 1.0)

            # Use same logic as classify() but optimized for loop
            regime = self._classify_from_features(current_feat)

            labels[i] = regime.label
            confidences[i] = regime.confidence
            transition_scores[i] = transition_score

        res_df = df.copy()
        res_df["regime_label"] = labels
        res_df["regime_confidence"] = confidences
        res_df["transition_score"] = transition_scores

        return res_df

    def _classify_from_features(self, features: pd.Series) -> MarketRegime:
        """Internal helper for classification from a feature row."""
        if features["rel_vol"] > 3.0:
            return MarketRegime(
                label=RegimeType.NEWS_SHOCK,
                confidence=min(features["rel_vol"] / 5.0, 1.0)
            )
        if features["rel_vol"] > 1.5 and abs(features["reg_slope"]) > features["atr"] * 0.1:
            return MarketRegime(label=RegimeType.VOLATILE_BREAKOUT, confidence=0.8)
        if abs(features["reg_slope"]) > features["atr"] * 0.05:
            return MarketRegime(label=RegimeType.TRENDING, confidence=0.7)
        if features["rel_vol"] < 0.8 and abs(features["reg_slope"]) > 0:
            return MarketRegime(label=RegimeType.LOW_VOLATILITY_DRIFT, confidence=0.6)
        if abs(features["slope"]) > features["bb_width"] * 0.5:
            return MarketRegime(label=RegimeType.MEAN_REVERSION, confidence=0.6)
        return MarketRegime(label=RegimeType.RANGING, confidence=0.5)
