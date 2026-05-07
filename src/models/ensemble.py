"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/ensemble.py
Ensemble voting system combining signals from multiple AI models:
  - PPO (Stable-Baselines3)
  - Dreamer V3 (world model RL)
  - LSTM + Multi-head Attention
Weighted confidence voting with model dissent checks and dynamic weight adaptation.

Author: triqbit
License: MIT
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Any, Dict, Optional

import numpy as np

try:
    import torch
except ImportError:
    torch = None  # type: ignore

from src.core.constants import SignalDirection
from src.core.profiler import profile
from src.models.base_model import BaseModel, Signal
from src.models.dreamer_agent import DreamerAgent
from src.models.dynamic_ensemble import DynamicEnsemble
from src.models.lstm_model import LSTMModel
from src.models.ppo_agent import PPOAgent

logger = logging.getLogger(__name__)


class EnsembleModel(BaseModel):
    """
    Weighted voting ensemble: PPO + Dreamer + LSTM-Attention.

    Delegates weight adaptation to DynamicEnsemble for robust rebalancing.
    Implements institutional consensus (60%) and dissent checks (veto).
    Uses standardized model wrappers for all sub-algorithms.
    """

    ALGORITHMS = ["ppo", "dreamer", "lstm"]

    def __init__(
        self,
        device: str = "cpu",
        consensus_threshold: float = 0.60,
        model_weights: Optional[Dict[str, float]] = None,
    ) -> None:
        """
        Initialize the EnsembleModel.

        Args:
            device: Computing device ('cpu', 'cuda', etc.).
            consensus_threshold: Required weighted agreement (default 60%).
            model_weights: Initial weights for each algorithm.
        """
        super().__init__()
        self.device = device
        self.dynamic_ensemble = DynamicEnsemble(
            model_names=self.ALGORITHMS, smoothing_factor=0.1, max_swing=0.05, min_weight=0.05
        )
        if model_weights:
            total = sum(model_weights.values())
            self.dynamic_ensemble.weights = {k: v / total for k, v in model_weights.items()}

        # Standardized model wrappers
        self.ppo_agent: Optional[PPOAgent] = None
        self.dreamer_agent: Optional[DreamerAgent] = None
        self.lstm_model: Optional[LSTMModel] = None

        self.consensus_threshold = consensus_threshold

        self._performance: Dict[str, deque[float]] = {k: deque(maxlen=200) for k in self.ALGORITHMS}
        self._last_confidences: Dict[str, deque[float]] = {
            k: deque(maxlen=200) for k in self.ALGORITHMS
        }
        self._latest_health_metrics: Dict[str, float] = {
            "accuracy": 1.0,
            "drift": 0.0,
            "calibration": 0.0,
        }

    @property
    def weights(self) -> Dict[str, float]:
        """Expose weights from dynamic_ensemble."""
        return self.dynamic_ensemble.get_weights()

    def aggregate_signals(self, signals: Dict[str, Signal]) -> Signal:
        """
        Aggregates pre-calculated signals from sub-models using weighted consensus.

        Args:
            signals: Dictionary of algorithm names and their predicted Signal.

        Returns:
            Signal: The aggregated consensus signal.
        """
        if not signals:
            return Signal(direction=SignalDirection.HOLD, confidence=0.0)

        # 1. Dissent Check: Veto if there are conflicting BUY and SELL signals
        has_buy = any(s.direction == SignalDirection.BUY for s in signals.values())
        has_sell = any(s.direction == SignalDirection.SELL for s in signals.values())

        if has_buy and has_sell:
            logger.warning("DISSENT VETO: Conflicting signals detected. Blocking execution.")
            return Signal(
                direction=SignalDirection.HOLD,
                confidence=0.0,
                metadata={
                    "reason": "Dissent conflict",
                    "votes": {k: s.direction.name for k, s in signals.items()},
                    "per_algo_votes": {k: s.direction for k, s in signals.items()},
                },
            )

        # 2. Weighted Aggregation
        weighted_buy_conf = 0.0
        weighted_sell_conf = 0.0
        weighted_hold_conf = 0.0

        total_active_weight = sum(self.weights.get(k, 0.0) for k in signals)
        if total_active_weight <= 0:
            return Signal(direction=SignalDirection.HOLD, confidence=0.0)

        for name, sig in signals.items():
            norm_weight = self.weights.get(name, 0.0) / total_active_weight
            if sig.direction == SignalDirection.BUY:
                weighted_buy_conf += sig.confidence * norm_weight
            elif sig.direction == SignalDirection.SELL:
                weighted_sell_conf += sig.confidence * norm_weight
            else:
                weighted_hold_conf += sig.confidence * norm_weight

        metadata = {
            "weighted_probs": {
                "BUY": weighted_buy_conf,
                "SELL": weighted_sell_conf,
                "HOLD": weighted_hold_conf,
            },
            "weights": self.weights,
            "votes": {k: s.direction.name for k, s in signals.items()},
            "per_algo_votes": {k: s.direction for k, s in signals.items()},
        }

        # 3. Consensus Threshold Check
        if weighted_buy_conf >= self.consensus_threshold:
            return Signal(direction=SignalDirection.BUY, confidence=weighted_buy_conf, metadata=metadata)
        elif weighted_sell_conf >= self.consensus_threshold:
            return Signal(direction=SignalDirection.SELL, confidence=weighted_sell_conf, metadata=metadata)
        else:
            return Signal(direction=SignalDirection.HOLD, confidence=weighted_hold_conf, metadata=metadata)

    def predict(
        self,
        features: np.ndarray,
        **kwargs: Any,
    ) -> Signal:
        """
        Generate a trading signal from input features using internal models.

        Args:
            features: Primary feature array for RL agents (PPO, Dreamer).
            **kwargs: Additional context (seq, regime_info).

        Returns:
            Signal: Consolidated ensemble signal.
        """
        seq = kwargs.get("seq")
        regime_info = kwargs.get("regime_info")
        votes: Dict[str, Signal] = {}

        # PPO prediction
        if self.ppo_agent is not None:
            with profile("inference_ppo"):
                votes["ppo"] = self.ppo_agent.predict(features, regime_info=regime_info)

        # Dreamer prediction
        if self.dreamer_agent is not None:
            with profile("inference_dreamer"):
                votes["dreamer"] = self.dreamer_agent.predict(features, regime_info=regime_info)

        # LSTM prediction
        if self.lstm_model is not None:
            with profile("inference_lstm"):
                lstm_input = seq if seq is not None else features
                votes["lstm"] = self.lstm_model.predict(lstm_input, regime_info=regime_info)

        return self.aggregate_signals(votes)


__all__ = ["EnsembleModel"]
