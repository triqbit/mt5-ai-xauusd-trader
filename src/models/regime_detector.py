"""
Market Regime Detection for XAUUSD Trading.
Classifies market state into distinct regimes based on statistical features.
"""

import logging
from enum import Enum
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


class RegimeLabel(str, Enum):
    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE_BREAKOUT = "volatile_breakout"
    LOW_VOL_DRIFT = "low_vol_drift"
    NEWS_SHOCK = "news_shock"
    MEAN_REVERSION = "mean_reversion"
    UNKNOWN = "unknown"


class MarketRegime(BaseModel):
    """
    Typed regime object containing classification results.
    """
    model_config = ConfigDict(frozen=True)

    label: RegimeLabel = Field(..., description="The detected market regime label.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of the classification (0-1).")
    transition_score: float = Field(..., description="Score indicating the likelihood of a regime transition.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional statistical features or model outputs.")


class RegimeDetector:
    """
    Detects market regimes using statistical analysis of OHLCV data.
    """

    def __init__(
        self,
        lookback_period: int = 20,
        volatility_threshold: float = 1.5,
        trend_threshold: float = 0.5,
    ) -> None:
        self.lookback_period = lookback_period
        self.volatility_threshold = volatility_threshold
        self.trend_threshold = trend_threshold

    def detect(self, df: pd.DataFrame) -> MarketRegime:
        """
        Detect the current regime from a DataFrame of OHLCV data.
        Expected columns: 'open', 'high', 'low', 'close', 'volume'
        """
        if len(df) < self.lookback_period:
            return MarketRegime(
                label=RegimeLabel.UNKNOWN,
                confidence=0.0,
                transition_score=0.0,
                metadata={"reason": "insufficient_data"},
            )

        features = self._calculate_features(df)
        label, confidence = self._classify(features)
        transition_score = self._calculate_transition_score(features, label)

        return MarketRegime(
            label=label,
            confidence=confidence,
            transition_score=transition_score,
            metadata=features,
        )

    def label_historical(self, df: pd.DataFrame) -> pd.Series:
        """
        Apply regime labeling to an entire historical dataset.
        """
        regimes = []
        for i in range(len(df)):
            if i < self.lookback_period:
                regimes.append(RegimeLabel.UNKNOWN)
                continue

            # Slice window for calculation
            window = df.iloc[max(0, i - self.lookback_period + 1) : i + 1]
            regime = self.detect(window)
            regimes.append(regime.label)

        return pd.Series(regimes, index=df.index)

    def _calculate_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate statistical features for regime classification.
        """
        close = df["close"]
        returns = close.pct_change().dropna()

        # Volatility: ATR relative to price
        high_low = df["high"] - df["low"]
        high_pc = (df["high"] - df["close"].shift(1)).abs()
        low_pc = (df["low"] - df["close"].shift(1)).abs()
        tr = pd.concat([high_low, high_pc, low_pc], axis=1).max(axis=1)
        atr = tr.rolling(self.lookback_period).mean().iloc[-1]
        relative_atr = (atr / close.iloc[-1]) * 100 if close.iloc[-1] != 0 else 0

        # Trend: Slope of price
        x = np.arange(len(close))
        y = close.values
        slope = np.polyfit(x, y, 1)[0]
        relative_slope = (slope / close.iloc[-1]) * 100 if close.iloc[-1] != 0 else 0

        # R-squared as trend strength
        y_pred = slope * x + np.polyfit(x, y, 1)[1]
        r_squared = 1 - (np.sum((y - y_pred)**2) / np.sum((y - y.mean())**2))

        # Volatility Clustering (Kurtosis of returns)
        kurtosis = returns.tail(self.lookback_period).kurtosis()

        # Efficiency Ratio (Fractal Dimension proxy)
        net_move = abs(close.iloc[-1] - close.iloc[0])
        sum_abs_moves = (close.diff().abs()).iloc[1:].sum()
        efficiency_ratio = net_move / sum_abs_moves if sum_abs_moves != 0 else 0

        return {
            "relative_atr": float(relative_atr),
            "relative_slope": float(relative_slope),
            "r_squared": float(r_squared),
            "kurtosis": float(kurtosis) if not np.isnan(kurtosis) else 0.0,
            "efficiency_ratio": float(efficiency_ratio),
            "current_price": float(close.iloc[-1]),
        }

    def _classify(self, features: Dict[str, Any]) -> Tuple[RegimeLabel, float]:
        """
        Heuristic-based classification logic.
        """
        rel_atr = features["relative_atr"]
        rel_slope = features["relative_slope"]
        r2 = features["r_squared"]
        er = features["efficiency_ratio"]
        kurt = features["kurtosis"]

        # 1. News Shock / Volatile Breakout
        # High relative ATR or high kurtosis (fat tails)
        if rel_atr > self.volatility_threshold * 2 or kurt > 10.0:
            if abs(rel_slope) > self.trend_threshold or er > 0.7:
                return RegimeLabel.NEWS_SHOCK, 0.85
            return RegimeLabel.VOLATILE_BREAKOUT, 0.80

        # 2. Trending
        # High R-squared and high Efficiency Ratio
        if r2 > 0.7 and er > 0.6:
            return RegimeLabel.TRENDING, min(0.9, r2)

        # 3. Low Volatility Drift
        # Low ATR, consistent but slow slope
        if rel_atr < self.volatility_threshold * 0.5 and abs(rel_slope) > self.trend_threshold * 0.2:
            return RegimeLabel.LOW_VOL_DRIFT, 0.75

        # 4. Mean Reversion / Ranging
        # Low efficiency ratio, price bouncing in range
        if er < 0.3:
            if rel_atr > self.volatility_threshold:
                return RegimeLabel.MEAN_REVERSION, 0.70
            return RegimeLabel.RANGING, 0.80

        # Default
        return RegimeLabel.RANGING, 0.50

    def _calculate_transition_score(self, features: Dict[str, Any], current_label: RegimeLabel) -> float:
        """
        Estimate the likelihood of transitioning to a different regime.
        Higher score means transition is more likely.
        """
        # Simple heuristic: as Efficiency Ratio or R-squared drops for a trending regime,
        # the transition score increases.
        er = features["efficiency_ratio"]
        r2 = features["r_squared"]

        if current_label == RegimeLabel.TRENDING:
            return 1.0 - min(er, r2)

        if current_label == RegimeLabel.RANGING:
            # Transition from ranging often happens with volatility spikes
            return min(features["relative_atr"] / self.volatility_threshold, 1.0)

        return 0.5
