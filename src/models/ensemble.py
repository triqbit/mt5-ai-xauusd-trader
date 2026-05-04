"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/ensemble.py
Ensemble voting system combining signals from multiple AI models.
Implements:
  - Weighted consensus logic (minimum 60% agreement)
  - Dissent checks (blocks BUY/SELL conflicts)
  - Weighted confidence requirement
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

import numpy as np

from src.core.constants import SignalDirection
from src.models.base_model import BaseModel, Signal

logger = logging.getLogger(__name__)

class EnsembleModel(BaseModel):
    """
    Weighted consensus ensemble for signal aggregation.
    """

    def __init__(self, model_weights: Dict[str, float] | None = None) -> None:
        """
        Initialize ensemble with optional model weights.
        """
        super().__init__()
        # Default weights if none provided
        self.weights = model_weights or {
            "ppo": 0.4,
            "lstm": 0.3,
            "dreamer": 0.3
        }
        # Standardize weights to sum to 1.0
        total = sum(self.weights.values())
        self.weights = {k: v / total for k, v in self.weights.items()}

        logger.info("EnsembleModel initialized with weights: %s", self.weights)

    def aggregate_signals(self, signals: Dict[str, Signal]) -> Signal:
        """
        Aggregates signals from multiple models using weighted consensus.

        Args:
            signals: Dictionary mapping model names to their Signal outputs.

        Returns:
            The final aggregated Signal.
        """
        if not signals:
            return Signal(direction=SignalDirection.HOLD, confidence=0.0)

        # 1. Dissent Check: Block if there are conflicting BUY and SELL signals
        has_buy = any(s.direction == SignalDirection.BUY for s in signals.values())
        has_sell = any(s.direction == SignalDirection.SELL for s in signals.values())

        if has_buy and has_sell:
            logger.warning("Dissent detected: BUY and SELL conflict. Returning HOLD.")
            return Signal(direction=SignalDirection.HOLD, confidence=0.0,
                          metadata={"reason": "Dissent conflict"})

        # 2. Weighted Consensus Calculation
        # Map SignalDirection to values for averaging
        # SignalDirection: HOLD=0, BUY=1, SELL=-1 (assumed based on standard practice)
        # We need to calculate weighted direction and weighted confidence.

        weighted_buy_conf = 0.0
        weighted_sell_conf = 0.0
        weighted_hold_conf = 0.0

        for name, sig in signals.items():
            weight = self.weights.get(name, 0.0)
            if sig.direction == SignalDirection.BUY:
                weighted_buy_conf += sig.confidence * weight
            elif sig.direction == SignalDirection.SELL:
                weighted_sell_conf += sig.confidence * weight
            else:
                weighted_hold_conf += sig.confidence * weight

        # 3. Decision Logic
        # Enforce 60% weighted confidence requirement for any action
        CONSENSUS_THRESHOLD = 0.60

        if weighted_buy_conf >= CONSENSUS_THRESHOLD:
            final_direction = SignalDirection.BUY
            final_confidence = weighted_buy_conf
        elif weighted_sell_conf >= CONSENSUS_THRESHOLD:
            final_direction = SignalDirection.SELL
            final_confidence = weighted_sell_conf
        else:
            final_direction = SignalDirection.HOLD
            final_confidence = weighted_hold_conf

        logger.info("Ensemble Result | Dir: %s | Conf: %.2f", final_direction, final_confidence)

        return Signal(
            direction=final_direction,
            confidence=final_confidence,
            metadata={
                "weighted_buy": weighted_buy_conf,
                "weighted_sell": weighted_sell_conf,
                "weighted_hold": weighted_hold_conf,
                "model_signals": {k: {"dir": s.direction, "conf": s.confidence} for k, s in signals.items()}
            }
        )

    def predict(self, features: np.ndarray, **kwargs: Any) -> Signal:
        """
        In a real scenario, this would trigger predict() on all sub-models.
        For the ensemble stub, we expect aggregate_signals to be called.
        """
        # Placeholder as Ensemble usually aggregates already generated signals
        return Signal(direction=SignalDirection.HOLD, confidence=0.0)

__all__ = ["EnsembleModel"]
