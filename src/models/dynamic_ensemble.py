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

from src.models.regime_detector import MarketRegime

logger = logging.getLogger(__name__)


class DynamicEnsemble:
    """
    Adaptive model weighting based on:
    - Recent accuracy (Sharpe/Win-rate)
    - Calibration error
    - Drift/Degradation signals
    - Market regime context
    """

    def __init__(
        self,
        model_names: List[str],
        smoothing_factor: float = 0.1,
        max_swing: float = 0.05,
        min_weight: float = 0.05,
    ) -> None:
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
        regime: Optional[MarketRegime] = None,
    ) -> Dict[str, float]:
        """
        Update weights based on performance and market context.
        metrics: {
            'model_name': {
                'accuracy': 0.0-1.0,
                'calibration_error': 0.0-1.0,
                'drift_score': 0.0-1.0
            }
        }
        """
        raw_scores: Dict[str, float] = {}

        for name in self.model_names:
            m = metrics.get(name, {})
            acc = m.get("accuracy", 0.5)
            cal = m.get("calibration_error", 0.0)
            drift = m.get("drift_score", 0.0)

            # Core scoring formula
            score = acc - (0.5 * cal) - (0.5 * drift)

            # Regime-based adjustments (XAUUSD heuristics)
            if regime == MarketRegime.NEWS_SHOCK:
                if drift > 0.5:
                    score -= 0.2
            elif regime == MarketRegime.RANGING:
                score -= 0.2 * cal

            raw_scores[name] = max(score, 0.01)

        # Normalize target weights with floor
        new_targets = self._normalize_with_floor(raw_scores, self.min_weight)

        # Calculate adjustments with smoothing and stability controls
        deltas: Dict[str, float] = {}
        for name in self.model_names:
            target = new_targets[name]
            current = self.weights[name]
            prev_target = self._prev_target_weights[name]

            # 1. Oscillation dampening:
            # If target and prev_target are on opposite sides of current, slow down
            if (target > current and prev_target < current) or (
                target < current and prev_target > current
            ):
                alpha = self.smoothing_factor * 0.5
            else:
                alpha = self.smoothing_factor

            # 2. EMA adaptation with swing cap
            diff = target - current
            deltas[name] = float(np.clip(diff * alpha, -self.max_swing, self.max_swing))

        # 3. Balance deltas to maintain sum=1 and respect constraints
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
