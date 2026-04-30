"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/dynamic_ensemble.py
Dynamic ensemble weighting logic for adaptive model combinations.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ModelMetrics:
    """Tracks performance and health metrics for an individual model."""

    accuracy: float = 0.5
    calibration_error: float = 0.0
    drift_score: float = 0.0
    recent_returns: List[float] = field(default_factory=list)


@dataclass
class MarketContext:
    """Represents current market conditions."""

    regime: str = "trending"  # e.g., trending, ranging, volatile
    volatility: float = 1.0  # normalized volatility


class DynamicEnsemble:
    """
    Adjusts model weights dynamically based on performance and market context.

    Implements decay logic, abrupt change caps, and oscillation dampening
    to ensure stable adaptation.
    """

    def __init__(
        self,
        model_names: List[str],
        initial_weights: Optional[Dict[str, float]] = None,
        ema_alpha: float = 0.1,
        max_weight_change: float = 0.05,
        min_weight: float = 0.05,
    ) -> None:
        """
        Initialize DynamicEnsemble.

        Args:
            model_names: Names of the models in the ensemble.
            initial_weights: Starting weights for each model.
            ema_alpha: Smoothing factor for weight updates (0 to 1).
            max_weight_change: Maximum allowed change in weight per update.
            min_weight: Minimum weight floor for any model to avoid starvation.
        """
        self.model_names = model_names
        self.ema_alpha = ema_alpha
        self.max_weight_change = max_weight_change
        self.min_weight = min_weight

        if initial_weights:
            self.weights = initial_weights
        else:
            equal_weight = 1.0 / len(model_names)
            self.weights = {name: equal_weight for name in model_names}

        self.metrics: Dict[str, ModelMetrics] = {name: ModelMetrics() for name in model_names}
        self.context = MarketContext()

        # To prevent oscillation, track previous target weights
        self._prev_target_weights: Dict[str, float] = self.weights.copy()

    def update_metrics(self, model_name: str, **kwargs: Any) -> None:
        """Update metrics for a specific model."""
        if model_name not in self.metrics:
            logger.warning("Model %s not recognized.", model_name)
            return

        metric_obj = self.metrics[model_name]
        for key, value in kwargs.items():
            if hasattr(metric_obj, key):
                setattr(metric_obj, key, value)
            else:
                logger.warning("Metric %s not recognized for ModelMetrics.", key)

    def update_context(self, regime: Optional[str] = None, volatility: Optional[float] = None) -> None:
        """Update the global market context."""
        if regime is not None:
            self.context.regime = regime
        if volatility is not None:
            self.context.volatility = volatility

    def _calculate_base_score(self, model_name: str) -> float:
        """Calculate a base raw score for a model based on its metrics."""
        m = self.metrics[model_name]

        # 1. Accuracy (0 to 1)
        score = m.accuracy * 1.0

        # 2. Calibration penalty (penalize higher error)
        score -= m.calibration_error * 0.5

        # 3. Drift penalty (penalize higher drift)
        score -= m.drift_score * 0.5

        # 4. Volatility adjustment
        # In high volatility, we might prefer models that handle it better.
        # For now, we apply a generic penalty if the model's recent returns are unstable.
        if len(m.recent_returns) > 5:
            vol = np.std(m.recent_returns)
            score -= vol * 0.1 * self.context.volatility

        return max(score, 0.01)

    def _apply_regime_bias(self, scores: Dict[str, float]) -> Dict[str, float]:
        """Adjust scores based on the current market regime."""
        # Example regime biases:
        # - "trending": prefer models with high historical trend-following accuracy
        # - "ranging": prefer models that handle mean reversion
        # - "volatile": prefer more conservative or robust models

        # This is a placeholder for more sophisticated logic.
        # For now, we just return the scores as is, but structured for expansion.
        biased_scores = scores.copy()

        if self.context.regime == "volatile":
            # In volatile regimes, slightly flatten the weights to reduce single-model risk
            avg_score = sum(biased_scores.values()) / len(biased_scores)
            for name in biased_scores:
                biased_scores[name] = 0.7 * biased_scores[name] + 0.3 * avg_score

        return biased_scores

    def step(self) -> Dict[str, float]:
        """
        Perform one iteration of weight adaptation.

        Returns:
            The updated weights.
        """
        # 1. Calculate raw target weights
        raw_scores = {name: self._calculate_base_score(name) for name in self.model_names}
        biased_scores = self._apply_regime_bias(raw_scores)

        total_score = sum(biased_scores.values())
        target_weights = {name: score / total_score for name, score in biased_scores.items()}

        # 2. Oscillation dampening
        # If the target weight has flipped direction relative to the current weight
        # compared to the previous target, we dampen the move to prevent rapid flip-flopping.
        for name in self.model_names:
            prev_target = self._prev_target_weights[name]
            current_weight = self.weights[name]
            target = target_weights[name]

            # If target direction is opposite to the previous target's direction, dampen it
            if (target > current_weight and prev_target < current_weight) or (
                target < current_weight and prev_target > current_weight
            ):
                target_weights[name] = 0.5 * (target + current_weight)

        self._prev_target_weights = target_weights.copy()

        # 3. Apply weights with EMA and caps
        new_weights = {}
        for name in self.model_names:
            target = target_weights[name]
            current = self.weights[name]

            # EMA Update
            updated = (1 - self.ema_alpha) * current + self.ema_alpha * target

            # Abrupt change cap
            diff = updated - current
            if abs(diff) > self.max_weight_change:
                updated = current + np.sign(diff) * self.max_weight_change

            new_weights[name] = max(updated, self.min_weight)

        # 4. Final normalization to ensure they sum to 1.0
        total_w = sum(new_weights.values())
        self.weights = {name: w / total_w for name, w in new_weights.items()}

        logger.debug("Dynamic weights updated: %s", self.weights)
        return self.weights.copy()

    def get_weights(self) -> Dict[str, float]:
        """Return the current ensemble weights."""
        return self.weights.copy()
