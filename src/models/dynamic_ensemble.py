"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/dynamic_ensemble.py
Dynamic weighting engine for model ensembles.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np

from src.models.regime_detector import MarketRegime, RegimeInfo

logger = logging.getLogger(__name__)

__all__ = ["DynamicEnsemble"]


class DynamicEnsemble:
    """
    Institutional-grade adaptive model weighting engine.

    Adjusts ensemble weights dynamically by combining performance metrics with
    market regime context. Employs several stability mechanisms to prevent
    overfitting to noise and ensure controlled rebalancing:

    1. EMA Decay: Weights move towards target scores via an Exponential Moving Average.
    2. Swing Caps: Maximum allowed change per update is strictly capped by `max_swing`.
    3. Oscillation Dampening: Detects 'flip-flopping' targets and aggressively
       reduces the adaptation rate to preserve portfolio stability.
    4. Volatility Scaling: Adaptation slows down automatically in high-volatility
       regimes to avoid reacting to transient price shocks.
    """

    def __init__(
        self,
        model_names: List[str],
        smoothing_factor: float = 0.1,
        max_swing: float = 0.05,
        min_weight: float = 0.05,
    ) -> None:
        """
        Initialize the dynamic ensemble engine.

        Args:
            model_names: List of model identifiers.
            smoothing_factor: EMA decay factor for weight updates.
            max_swing: Maximum allowed weight change per update.
            min_weight: Minimum weight floor for any single model.
        """
        if not model_names:
            raise ValueError("model_names cannot be empty")

        self.model_names = model_names
        self.smoothing_factor = smoothing_factor  # EMA decay
        self.max_swing = max_swing  # Cap on abrupt changes
        self.min_weight = min_weight  # Floor per model

        # Initialize equal weights
        n = len(model_names)
        self.weights = dict.fromkeys(model_names, 1.0 / n)
        self._target_weights = self.weights.copy()
        self._prev_target_weights = self.weights.copy()

    def update_weights(
        self,
        metrics: Dict[str, Dict[str, float]],
        regime_info: Optional[RegimeInfo] = None,
        volatility_context: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Update ensemble weights using a multi-factor scoring model and stability controls.

        Args:
            metrics: Dictionary mapping model names to their performance metrics:
                - accuracy: Normalized Sharpe or Win-rate (0.0 to 1.0).
                - calibration_error: Deviation between confidence and success (0.0 to 1.0).
                - drift_score: Signal of performance degradation (0.0 to 1.0).
            regime_info: Current market regime context for heuristic-based scoring adjustments.
            volatility_context: Optional manual override or additional volatility metric.

        Returns:
            Dict[str, float]: The updated weight distribution (sums to 1.0).
        """
        if not metrics:
            return self.weights

        raw_scores: Dict[str, float] = {}

        regime = regime_info.label if regime_info else MarketRegime.UNKNOWN

        # Determine volatility: prefer explicit context, then regime info, default to 1.0
        volatility = 1.0
        if volatility_context is not None:
            volatility = volatility_context
        elif regime_info is not None:
            volatility = regime_info.volatility_index

        for name in self.model_names:
            m = metrics.get(name, {})
            acc = m.get("accuracy", 0.5)
            cal = m.get("calibration_error", 0.0)
            drift = m.get("drift_score", 0.0)

            # Core scoring formula: High weight on accuracy, penalized by drift and miscalibration.
            score = acc - (0.3 * cal) - (0.4 * drift)

            # Regime-based adjustments (XAUUSD heuristics)
            if regime == MarketRegime.NEWS_SHOCK:
                # In news shocks, penalize drifting models heavily
                if drift > 0.5:
                    score -= 0.2
            elif regime == MarketRegime.RANGING:
                # In ranging markets, calibration is slightly more important to avoid fakeouts
                score -= 0.2 * cal
            elif regime == MarketRegime.TRENDING:
                # In trending markets, favor models with low drift (consistency)
                score -= 0.3 * drift
            elif regime == MarketRegime.VOLATILE_BREAKOUT:
                # In breakouts, calibration is critical for stop-loss reliability
                score -= 0.4 * cal
            elif regime == MarketRegime.MEAN_REVERSION:
                # In mean reversion, overconfidence is deadly
                score -= 0.5 * cal
            elif regime == MarketRegime.LOW_VOLATILITY_DRIFT:
                # Drift is expected, but accuracy is paramount
                score += 0.1 * acc

            # Volatility context (penalize uncalibrated models in high volatility)
            if volatility > 2.0:
                score -= 0.3 * cal

            raw_scores[name] = max(score, 0.01)

        # Normalize target weights with floor
        new_targets = self._normalize_with_floor(raw_scores, self.min_weight)

        # Calculate adjustments with smoothing and stability controls
        deltas: Dict[str, float] = {}
        for name in self.model_names:
            target = new_targets[name]
            current = self.weights[name]
            prev_target = self._target_weights[name]

            # 1. Dynamic smoothing and oscillation dampening:
            # If target and prev_target are on opposite sides of current, it indicates oscillation
            is_oscillating = (target > current and prev_target < current) or (
                target < current and prev_target > current
            )

            # Reduce alpha in high volatility or when oscillating to preserve stability
            vol_factor = float(np.clip(2.0 / (volatility + 1.0), 0.2, 1.0))
            alpha = self.smoothing_factor * vol_factor
            if is_oscillating:
                # Aggressive dampening on flip-flops (Oscillation Prevention)
                alpha *= 0.2

            # 2. EMA adaptation (Decay Logic) with safety cap (Swing Cap)
            diff = target - current
            # Limit the step size to max_swing to ensure stability
            deltas[name] = float(np.clip(diff * alpha, -self.max_swing, self.max_swing))

        # 3. Balance deltas to maintain sum=1 and respect constraints
        # Sum of deltas must be 0 to keep weights sum = 1
        pos_sum = sum(d for d in deltas.values() if d > 0)
        neg_sum = sum(abs(d) for d in deltas.values() if d < 0)

        if pos_sum > 1e-9 and neg_sum > 1e-9:
            if pos_sum > neg_sum:
                # Scale down positive deltas
                ratio = neg_sum / pos_sum
                for name in deltas:
                    if deltas[name] > 0:
                        deltas[name] *= ratio
            else:
                # Scale down negative deltas
                ratio = pos_sum / neg_sum
                for name in deltas:
                    if deltas[name] < 0:
                        deltas[name] *= ratio
        elif pos_sum > 1e-9 or neg_sum > 1e-9:
            # Unbalanced deltas (should be rare if current and target both sum to 1)
            deltas = dict.fromkeys(deltas, 0.0)

        # Apply adjustments
        for name in self.model_names:
            self.weights[name] += deltas[name]

        # Final re-normalization for float precision
        total_w = sum(self.weights.values())
        self.weights = {name: w / total_w for name, w in self.weights.items()}

        # Store targets for next oscillation check
        self._prev_target_weights = self._target_weights.copy()
        self._target_weights = new_targets.copy()

        logger.debug("Ensemble weights updated: %s", self.weights)
        return self.weights

    def _normalize_with_floor(self, scores: Dict[str, float], floor: float) -> Dict[str, float]:
        """Normalize scores to sum to 1.0 while respecting a minimum floor."""
        n = len(scores)
        if n * floor >= 1.0:
            return dict.fromkeys(scores, 1.0 / n)

        # Start all at floor
        weights = dict.fromkeys(scores, floor)
        remaining = 1.0 - (n * floor)

        # Distribute remaining proportionally to excess scores above a baseline
        # Use a small epsilon to avoid division by zero
        excess_scores = {name: max(0.0, scores[name] - 0.01) for name in scores}
        total_excess = sum(excess_scores.values())

        if total_excess > 1e-9:
            for name in scores:
                weights[name] += (excess_scores[name] / total_excess) * remaining
        else:
            # If no one is above baseline, distribute equally
            for name in scores:
                weights[name] += remaining / n
        return weights

    def get_weights(self) -> Dict[str, float]:
        """Return current ensemble weights."""
        return self.weights.copy()

    def __repr__(self) -> str:
        return f"DynamicEnsemble(models={self.model_names}, weights={self.weights})"
