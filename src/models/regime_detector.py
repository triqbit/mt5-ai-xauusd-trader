"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/regime_detector.py
Market regime detection for XAUUSD.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Tuple

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MarketRegime(str, Enum):
    """XAUUSD Market Regimes."""

    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE_BREAKOUT = "volatile_breakout"
    LOW_VOLATILITY_DRIFT = "low_volatility_drift"
    NEWS_SHOCK = "news_shock"
    MEAN_REVERSION = "mean_reversion"
    UNKNOWN = "unknown"


class RegimeInfo(BaseModel):
    """Structured regime detection output."""

    label: MarketRegime = Field(..., description="Detected regime label")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    transition_score: float = Field(..., description="Likelihood of a regime transition")
    volatility_index: float = Field(..., description="Normalized volatility metric")


class RegimeDetector:
    """
    Detects market regimes using statistical price features.
    Optimized for XAUUSD M5/M15 timeframes.
    """

    def __init__(self, window: int = 20, long_window: int = 100) -> None:
        self.window = window
        self.long_window = long_window
        self._last_regime: MarketRegime = MarketRegime.UNKNOWN

    def _calculate_efficiency_ratio(self, prices: np.ndarray) -> float:
        """Kaufman Efficiency Ratio: net change / sum of absolute changes."""
        if len(prices) < 2:
            return 0.0
        net_change = abs(prices[-1] - prices[0])
        abs_changes = np.abs(np.diff(prices))
        sum_abs_changes = np.sum(abs_changes)
        return float(net_change / (sum_abs_changes + 1e-9))

    def _calculate_slope(self, prices: np.ndarray) -> float:
        """Normalized linear regression slope."""
        n = len(prices)
        if n < 2:
            return 0.0
        x = np.arange(n)
        y = prices
        denom = n * np.sum(x**2) - (np.sum(x)) ** 2
        if abs(denom) < 1e-9:
            return 0.0
        slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / denom
        return float(slope / (prices[0] + 1e-9))

    def _calculate_volatility_clustering(self, returns: np.ndarray) -> float:
        """
        Calculates volatility clustering via autocorrelation of absolute returns.
        """
        if len(returns) < 10:
            return 0.0
        abs_rets = np.abs(returns)

        x = abs_rets[1:]
        y = abs_rets[:-1]

        if np.std(x) < 1e-9 or np.std(y) < 1e-9:
            return 0.0

        correlation_matrix = np.corrcoef(x, y)
        if correlation_matrix.shape == (2, 2):
            corr = correlation_matrix[0, 1]
            return float(corr) if not np.isnan(corr) else 0.0
        return 0.0

    def detect(self, data: pd.DataFrame) -> RegimeInfo:
        """
        Detect current market regime from OHLCV data.
        """
        if len(data) < self.long_window:
            return RegimeInfo(
                label=MarketRegime.UNKNOWN,
                confidence=0.0,
                transition_score=0.0,
                volatility_index=0.0,
            )

        lookback = self.long_window + 1
        subset = data.iloc[-lookback:]
        close = subset["close"].values
        high = subset["high"].values
        low = subset["low"].values

        # 1. Volatility (ATR Ratio)
        tr = np.maximum(
            high[1:] - low[1:],
            np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])),
        )
        if len(subset) <= self.long_window:
            tr = np.insert(tr, 0, high[0] - low[0])

        atr_short = np.mean(tr[-self.window :])
        atr_long = np.mean(tr[-self.long_window :])
        atr_ratio = atr_short / (atr_long + 1e-9)

        # 2. Efficiency Ratio
        er = self._calculate_efficiency_ratio(close[-self.window :])

        # 3. Price Slope
        slope = self._calculate_slope(close[-self.window :])

        # 4. Z-Score
        ma = np.mean(close[-self.window :])
        std = np.std(close[-self.window :]) + 1e-9
        z_score = (close[-1] - ma) / std

        # 5. Volatility Clustering
        returns = np.diff(close) / (close[:-1] + 1e-9)
        vc = self._calculate_volatility_clustering(returns[-self.window :])

        label, confidence, transition_score = self._apply_regime_logic(
            atr_ratio, er, slope, z_score, vc
        )

        regime_info = RegimeInfo(
            label=label,
            confidence=float(np.clip(confidence, 0.0, 1.0)),
            transition_score=float(np.clip(transition_score, 0.0, 1.0)),
            volatility_index=float(atr_ratio),
        )

        if label != self._last_regime:
            logger.debug("Regime transition: %s -> %s", self._last_regime, label)
            self._last_regime = label

        return regime_info

    def _apply_regime_logic(
        self, atr_ratio: float, er: float, slope: float, z_score: float, vc: float
    ) -> Tuple[MarketRegime, float, float]:
        """Heuristic logic to classify market regime."""
        label = MarketRegime.RANGING
        confidence = 0.5

        if atr_ratio > 2.5 and er > 0.7:
            label = MarketRegime.NEWS_SHOCK
            confidence = min(atr_ratio / 5.0, 1.0)
        elif atr_ratio > 1.25 and er > 0.5:
            label = MarketRegime.VOLATILE_BREAKOUT
            confidence = er
        elif er > 0.4 and abs(slope) > 0.00006:
            label = MarketRegime.TRENDING
            confidence = er
        elif abs(z_score) > 1.8 and er < 0.4:
            label = MarketRegime.MEAN_REVERSION
            confidence = min(abs(z_score) / 4.0, 1.0)
        elif atr_ratio < 0.9 and abs(slope) > 0.00003:
            label = MarketRegime.LOW_VOLATILITY_DRIFT
            confidence = 0.7
        else:
            label = MarketRegime.RANGING
            confidence = 1.0 - er

        transition_score = abs(atr_ratio - 1.0) * 0.4 + abs(er - 0.5) * 0.4 + abs(vc) * 0.2
        return label, confidence, transition_score

    def generate_summary(self, df: pd.DataFrame) -> Any:
        """
        Analyze a historical DataFrame and generate a RegimeSection for ResearchReporter.
        """
        from src.research.reporting import RegimeSection, RegimeSummary

        if "regime" not in df.columns:
            df = self.label_history(df)

        counts = df["regime"].value_counts(normalize=True) * 100

        # Calculate avg duration (rough estimate from changes)
        df["regime_change"] = df["regime"] != df["regime"].shift(1)
        regime_switches = df["regime_change"].sum()
        avg_duration = len(df) / regime_switches if regime_switches > 0 else len(df)

        regime_list = []
        for label, freq in counts.items():
            # Determine profitability if 'returns' column exists
            profitability = "N/A"
            if "returns" in df.columns:
                pnl = df[df["regime"] == label]["returns"].mean()
                profitability = "High" if pnl > 0.0001 else ("Low" if pnl < -0.0001 else "Neutral")

            regime_list.append(
                RegimeSummary(
                    label=str(label),
                    frequency_pct=float(freq),
                    avg_duration_bars=int(avg_duration),  # Simplified
                    profitability=profitability,
                )
            )

        return RegimeSection(
            summary=f"Detected {len(counts)} distinct market regimes.",
            regimes=regime_list,
            transition_insights=f"Average regime stability: {avg_duration:.1f} bars.",
        )

    def label_history(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Adds regime columns to historical DataFrame.
        """
        df = data.copy()
        regimes = [MarketRegime.UNKNOWN.value] * len(df)
        confidences = [0.0] * len(df)
        transition_scores = [0.0] * len(df)
        volatility_indices = [0.0] * len(df)

        for i in range(self.long_window - 1, len(df)):
            info = self.detect(df.iloc[: i + 1])
            regimes[i] = info.label.value
            confidences[i] = info.confidence
            transition_scores[i] = info.transition_score
            volatility_indices[i] = info.volatility_index

        df["regime"] = regimes
        df["regime_confidence"] = confidences
        df["regime_transition_score"] = transition_scores
        df["volatility_index"] = volatility_indices
        return df
