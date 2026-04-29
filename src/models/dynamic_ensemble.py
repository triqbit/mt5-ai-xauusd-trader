"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/dynamic_ensemble.py
Dynamic weight adaptation for ensemble models based on market context
and model performance metrics.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import Dict, List, Optional

import numpy as np
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MarketRegime(str, Enum):
    """Enumeration of identified market regimes."""
    TRENDING = "TRENDING"
    RANGING = "RANGING"
    VOLATILE_BREAKOUT = "VOLATILE_BREAKOUT"
    LOW_VOL_DRIFT = "LOW_VOL_DRIFT"
    NEWS_SHOCK = "NEWS_SHOCK"
    MEAN_REVERSION = "MEAN_REVERSION"
    UNKNOWN = "UNKNOWN"


class MarketContext(BaseModel):
    """Current market conditions for ensemble adaptation."""
    regime: MarketRegime = MarketRegime.UNKNOWN
    volatility_z_score: float = Field(default=0.0, description="ATR or StdDev Z-score")
    spread_ratio: float = Field(default=1.0, description="Current spread / median spread")


class ModelPerformance(BaseModel):
    """Per-model performance and health metrics."""
    accuracy: float = Field(default=0.5, ge=0.0, le=1.0)
    calibration_error: float = Field(default=0.0, ge=0.0, le=1.0)
    recent_pnl: float = 0.0
    drift_signal: float = Field(default=0.0, ge=0.0, le=1.0, description="PSI or similar drift metric")
    last_update_trades: int = 0


class DynamicWeightAdapter:
    """
    Intelligently adapts ensemble weights based on market context and
    model performance while maintaining stability.
    """

    def __init__(
        self,
        algorithms: List[str],
        base_weights: Optional[Dict[str, float]] = None,
        ema_alpha: float = 0.1,
        max_swing: float = 0.05,
        min_weight: float = 0.05,
    ) -> None:
        self.algorithms = algorithms
        self.ema_alpha = ema_alpha
        self.max_swing = max_swing
        self.min_weight = min_weight

        if base_weights:
            self.current_weights = {alg: base_weights.get(alg, 1.0 / len(algorithms)) for alg in algorithms}
        else:
            self.current_weights = {alg: 1.0 / len(algorithms) for alg in algorithms}

        self._normalize_weights()
        self.target_weights = self.current_weights.copy()

        # Regime affinity mapping: How well each model typically performs in each regime
        # This could be learned or set by domain expertise. Initialized neutrally.
        self.regime_affinity: Dict[MarketRegime, Dict[str, float]] = {
            regime: {alg: 1.0 for alg in algorithms} for regime in MarketRegime
        }

    def _normalize_weights(self) -> None:
        """Ensure weights sum to 1.0 and respect min_weight."""
        n = len(self.algorithms)
        if n == 0:
            return

        # 1. Ensure all weights are at least min_weight
        for alg in self.algorithms:
            self.current_weights[alg] = max(self.current_weights.get(alg, 0.0), self.min_weight)

        # 2. Re-distribute the excess/deficit to sum to 1.0
        # If sum of min_weights > 1.0, we just normalize equally
        if self.min_weight * n > 1.0:
            self.current_weights = {alg: 1.0 / n for alg in self.algorithms}
            return

        total_current = sum(self.current_weights.values())
        if total_current == 0:
             self.current_weights = {alg: 1.0 / n for alg in self.algorithms}
             return

        # We want: w_i = min_weight + (1 - n*min_weight) * (w_i - min_weight) / sum(w_j - min_weight)
        excess_to_distribute = 1.0 - (n * self.min_weight)
        current_excess_sum = total_current - (n * self.min_weight)

        if current_excess_sum > 1e-9:
            for alg in self.algorithms:
                relative_excess = (self.current_weights[alg] - self.min_weight) / current_excess_sum
                self.current_weights[alg] = self.min_weight + excess_to_distribute * relative_excess
        else:
            # All are at min_weight or very close, just distribute equally
            self.current_weights = {alg: 1.0 / n for alg in self.algorithms}

        # Final pass for floating point precision
        total = sum(self.current_weights.values())
        self.current_weights = {alg: w / total for alg, w in self.current_weights.items()}

    def get_weights(
        self,
        context: MarketContext,
        performance: Dict[str, ModelPerformance],
    ) -> Dict[str, float]:
        """
        Calculate and update weights based on new information.
        Returns the updated weights.
        """
        new_targets: Dict[str, float] = {}

        for alg in self.algorithms:
            perf = performance.get(alg, ModelPerformance())

            # 1. Base affinity for the current regime
            score = self.regime_affinity.get(context.regime, {}).get(alg, 1.0)

            # 2. Adjust by recent accuracy (0.5 is neutral)
            score *= (0.5 + perf.accuracy)

            # 3. Penalize by calibration error
            score *= (1.0 - perf.calibration_error)

            # 4. Penalize by drift/degradation
            score *= (1.0 - perf.drift_signal)

            # 5. Volatility context: some models might be better in high vol
            # (Heuristic: reduce weights of all if vol is extremely high/shock, favoring stable models)
            if context.regime == MarketRegime.NEWS_SHOCK or context.volatility_z_score > 3.0:
                # In shocks, we might want to dampen everything or favor a specific 'safe' model
                pass

            new_targets[alg] = score

        # Normalize targets
        total_target = sum(new_targets.values())
        if total_target > 0:
            new_targets = {alg: s / total_target for alg, s in new_targets.items()}
        else:
            new_targets = {alg: 1.0 / len(self.algorithms) for alg in self.algorithms}

        # Apply EMA and Clipping for stability
        for alg in self.algorithms:
            # Target weight for this step
            target = new_targets[alg]

            # Calculate delta
            diff = target - self.current_weights[alg]

            # Limit the swing in a single update
            diff = np.clip(diff, -self.max_swing, self.max_swing)

            # Apply EMA smoothing
            self.current_weights[alg] += self.ema_alpha * diff

        self._normalize_weights()
        return self.current_weights.copy()

    def set_regime_affinity(self, regime: MarketRegime, affinities: Dict[str, float]) -> None:
        """Manually tune or update regime affinities."""
        if regime in self.regime_affinity:
            for alg, val in affinities.items():
                if alg in self.algorithms:
                    self.regime_affinity[regime][alg] = val
