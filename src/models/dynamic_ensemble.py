"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/dynamic_ensemble.py
Dynamic weight adaptation for ensemble models based on market context and performance.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MarketContext(BaseModel):
    """
    Represents the current market state for weight adaptation.
    """
    regime: str = Field(..., description="Detected market regime (e.g., 'trending', 'ranging')")
    volatility: float = Field(..., description="Normalized volatility metric (e.g., ATR-based)")
    drift_detected: bool = Field(default=False, description="Whether significant market drift is detected")


class ModelPerformance(BaseModel):
    """
    Recent performance metrics for a specific model in the ensemble.
    """
    accuracy: float = Field(default=0.5, ge=0.0, le=1.0)
    calibration_score: float = Field(default=0.5, ge=0.0, le=1.0, description="1.0 - ECE (lower ECE is better)")
    degradation_signal: float = Field(default=0.0, ge=0.0, le=1.0, description="0.0 = stable, 1.0 = failing")


class DynamicWeightAdapter:
    """
    Intelligently adjusts model weights in an ensemble.

    Features:
    - EMA-based weight smoothing (decay logic)
    - Clipping of abrupt weight changes (caps)
    - Minimum weight thresholds to ensure diversity
    - Market-aware scoring
    """

    def __init__(
        self,
        model_names: List[str],
        initial_weights: Optional[Dict[str, float]] = None,
        decay_factor: float = 0.9,
        max_weight_change: float = 0.1,
        min_weight: float = 0.05,
    ) -> None:
        """
        Initialize the adapter.

        Args:
            model_names: List of model identifiers.
            initial_weights: Optional starting weights. Defaults to equal weights.
            decay_factor: Smoothing factor for EMA (higher = slower adaptation).
            max_weight_change: Maximum allowed change per update for stability.
            min_weight: Minimum weight for any single model.
        """
        self.model_names = model_names
        self.decay_factor = decay_factor
        self.max_weight_change = max_weight_change
        self.min_weight = min_weight

        if initial_weights:
            # Ensure all models are present
            self.current_weights = {name: initial_weights.get(name, 1.0 / len(model_names)) for name in model_names}
        else:
            self.current_weights = {name: 1.0 / len(model_names) for name in model_names}

        self._normalize_weights()

    def _normalize_weights(self) -> None:
        """Ensure weights sum to 1.0 while respecting min_weight."""
        # First pass: enforce min_weight
        for name in self.current_weights:
            self.current_weights[name] = max(self.current_weights[name], self.min_weight)

        # Second pass: normalize
        total = sum(self.current_weights.values())
        if total > 0:
            self.current_weights = {k: v / total for k, v in self.current_weights.items()}
        else:
            # Fallback to equal weights
            self.current_weights = {k: 1.0 / len(self.model_names) for k in self.model_names}

    def get_weights(self) -> Dict[str, float]:
        """Return the current weights."""
        return self.current_weights.copy()

    def update_weights(
        self,
        performance_data: Dict[str, ModelPerformance],
        market_context: MarketContext,
    ) -> Dict[str, float]:
        """
        Update weights based on performance and market conditions.

        Args:
            performance_data: Map of model name to its recent performance metrics.
            market_context: Current market environment details.

        Returns:
            The updated weight dictionary.
        """
        raw_scores: Dict[str, float] = {}

        for name in self.model_names:
            perf = performance_data.get(name, ModelPerformance())

            # Base score from accuracy and calibration
            # We want high accuracy, high calibration (well-calibrated), low degradation
            score = perf.accuracy * perf.calibration_score * (1.0 - perf.degradation_signal)

            # Regime-specific adjustments
            # For example, if market is drifting, we might penalize all models or look for specific ones
            if market_context.drift_detected:
                # If drifting, we generally reduce scores to force more conservative weighting
                # (though normalization makes this relative)
                score *= 0.8

            # Volatility context
            # High volatility might favor models with better calibration (risk awareness)
            if market_context.volatility > 2.0:  # Threshold for "high" volatility
                score *= perf.calibration_score

            # Regime specific preferences could be added here
            # if market_context.regime == "trending" and name == "ppo": score *= 1.2

            raw_scores[name] = max(score, 1e-6)

        # Calculate target weights from scores
        total_score = sum(raw_scores.values())
        target_weights = {name: score / total_score for name, score in raw_scores.items()}

        # Apply adaptation with stability constraints
        new_weights: Dict[str, float] = {}
        for name in self.model_names:
            prev_w = self.current_weights[name]
            target_w = target_weights[name]

            # 1. Decay/Smoothing (EMA)
            # new = decay * old + (1-decay) * target
            updated_w = (self.decay_factor * prev_w) + ((1.0 - self.decay_factor) * target_w)

            # 2. Caps on abrupt weight swings
            diff = updated_w - prev_w
            if abs(diff) > self.max_weight_change:
                updated_w = prev_w + (float(np.sign(diff)) * self.max_weight_change)

            new_weights[name] = updated_w

        self.current_weights = new_weights
        self._normalize_weights()

        logger.info(
            "Ensemble weight update | regime=%s vol=%.2f weights=%s",
            market_context.regime,
            market_context.volatility,
            {k: round(v, 4) for k, v in self.current_weights.items()}
        )

        return self.current_weights
