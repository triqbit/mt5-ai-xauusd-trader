"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/dynamic_ensemble.py
Dynamic ensemble weighting system that adapts to market conditions.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MarketRegime(str, Enum):
    """Enumeration of market regimes."""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"


class ModelPerformance(BaseModel):
    """Tracking metrics for an individual model in the ensemble."""
    accuracy: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence_calibration: float = Field(default=1.0, ge=0.0)  # Expected / Observed confidence
    drift_signal: float = Field(default=0.0, ge=0.0, le=1.0)  # 0 = no drift, 1 = total degradation
    last_updated_step: int = 0


class DynamicEnsemble:
    """
    Adjusts model weights dynamically based on market context and model performance.
    Implements stability controls to prevent oscillation and abrupt swings.
    """

    def __init__(
        self,
        model_names: List[str],
        initial_weights: Optional[Dict[str, float]] = None,
        max_weight_change: float = 0.1,
        smoothing_factor: float = 0.3,
        decay_rate: float = 0.95,
        min_weight: float = 0.05,
    ) -> None:
        """
        Initialize the dynamic ensemble.

        Args:
            model_names: List of model identifiers.
            initial_weights: Optional starting weights. Defaults to equal weighting.
            max_weight_change: Maximum allowed change in a single weight update.
            smoothing_factor: Factor for exponential smoothing (0 to 1). Higher = faster adaptation.
            decay_rate: Rate at which older performance signals decay.
            min_weight: Minimum weight floor for any model to ensure ensemble diversity.
        """
        self.model_names = model_names
        self.max_weight_change = max_weight_change
        self.smoothing_factor = smoothing_factor
        self.decay_rate = decay_rate
        self.min_weight = min_weight

        if initial_weights:
            self.weights = initial_weights
        else:
            self.weights = {name: 1.0 / len(model_names) for name in model_names}

        self.performance_history: Dict[str, ModelPerformance] = {
            name: ModelPerformance() for name in model_names
        }

        # Mapping of regime to model preference (example heuristic)
        # In a real scenario, this could be learned or provided by the researcher.
        self.regime_bias: Dict[MarketRegime, Dict[str, float]] = {
            MarketRegime.TRENDING_UP: {},
            MarketRegime.TRENDING_DOWN: {},
            MarketRegime.RANGING: {},
            MarketRegime.HIGH_VOLATILITY: {},
        }

        logger.info(
            "DynamicEnsemble initialised with models: %s | weights: %s",
            model_names,
            self.weights,
        )

    def update_weights(
        self,
        market_regime: MarketRegime,
        accuracies: Dict[str, float],
        calibrations: Dict[str, float],
        volatility: float,
        drift_signals: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Calculate and update ensemble weights based on multi-factor input.

        Args:
            market_regime: Current market environment.
            accuracies: Recent predictive accuracy for each model.
            calibrations: Confidence calibration metrics.
            volatility: Current market volatility.
            drift_signals: Detected drift/degradation for each model.

        Returns:
            Updated weights dictionary.
        """
        raw_scores = {}

        for name in self.model_names:
            perf = self.performance_history[name]

            # 1. Update performance metrics with decay logic
            perf.accuracy = (perf.accuracy * self.decay_rate) + (accuracies.get(name, 0.5) * (1 - self.decay_rate))
            perf.confidence_calibration = calibrations.get(name, 1.0)
            perf.drift_signal = drift_signals.get(name, 0.0)

            # 2. Calculate raw score for this update
            # High accuracy + good calibration - drift penalty
            score = perf.accuracy * (1.0 / (abs(1.0 - perf.confidence_calibration) + 1.0))
            score *= (1.0 - perf.drift_signal)

            # 3. Volatility adjustment
            # Some models might perform better/worse in high volatility
            if market_regime == MarketRegime.HIGH_VOLATILITY:
                # Example: Penalize scores more in high vol unless they are very accurate
                score *= 0.8 if perf.accuracy < 0.6 else 1.0

            raw_scores[name] = max(score, 1e-6)

        # 4. Normalize raw scores to get target weights
        total_score = sum(raw_scores.values())
        target_weights = {name: (score / total_score) for name, score in raw_scores.items()}

        # 5. Apply smoothing and caps to prevent oscillation and abrupt swings
        new_weights = {}
        for name in self.model_names:
            current_w = self.weights[name]
            target_w = target_weights[name]

            # Calculate change
            delta = target_w - current_w

            # Apply max change cap
            delta = max(min(delta, self.max_weight_change), -self.max_weight_change)

            # Apply smoothing (EMA-like update)
            smoothed_w = current_w + (delta * self.smoothing_factor)

            # Ensure floor
            new_weights[name] = max(smoothed_w, self.min_weight)

        # 6. Final normalization to ensure sum = 1.0
        total_new_w = sum(new_weights.values())
        self.weights = {name: (w / total_new_w) for name, w in new_weights.items()}

        logger.debug("Weights updated for regime %s: %s", market_regime, self.weights)
        return self.weights

    def get_weights(self) -> Dict[str, float]:
        """Return current ensemble weights."""
        return self.weights
