"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/ensemble.py
Ensemble voting system combining:
  - PPO (Stable-Baselines3)
  - Dreamer V3 (world model RL)
  - LSTM + Multi-head Attention
Weighted confidence voting with dynamic weight adaptation.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from collections import deque
from pathlib import Path
from typing import Dict, Optional

import numpy as np

try:
    import torch
    import torch.nn as nn
except ImportError:
    torch = None  # type: ignore
    nn = None  # type: ignore

from src.core.constants import ModelAction, SignalDirection
from src.models.base_model import BaseModel, Signal
from src.models.lstm_model import LSTMAttentionModel
from src.models.dynamic_ensemble import DynamicEnsemble
from src.models.regime_detector import RegimeInfo

logger = logging.getLogger(__name__)


# ── Ensemble orchestrator ─────────────────────────────────────────────────
class EnsembleModel(BaseModel):
    """
    Weighted voting ensemble: PPO + Dreamer + LSTM-Attention.
    Delegates weight adaptation to DynamicEnsemble for robust rebalancing.
    """

    ALGORITHMS = ["ppo", "dreamer", "lstm"]

    def __init__(self, device: str = "cpu") -> None:
        super().__init__()
        self.device = torch.device(device) if torch else None
        self.dynamic_ensemble = DynamicEnsemble(
            model_names=self.ALGORITHMS, smoothing_factor=0.1, max_swing=0.05, min_weight=0.05
        )
        self._ppo_model = None  # loaded lazily
        self._dreamer_model = None  # loaded lazily
        self.lstm_model: Optional[LSTMAttentionModel] = None
        # Internal cache for compatibility with existing record_return calls
        # Using deque for memory safety in long-running processes
        self._performance: Dict[str, deque[float]] = {k: deque(maxlen=200) for k in self.ALGORITHMS}
        self._last_confidences: Dict[str, deque[float]] = {
            k: deque(maxlen=200) for k in self.ALGORITHMS
        }

    @property
    def weights(self) -> Dict[str, float]:
        """Expose weights from dynamic_ensemble."""
        return self.dynamic_ensemble.get_weights()

    # ── Loading ────────────────────────────────────────────────────────────
    def load_ppo(self, path: Path) -> None:
        """Load a Stable-Baselines3 PPO checkpoint."""
        try:
            from stable_baselines3 import PPO

            self._ppo_model = PPO.load(str(path), device=self.device)
            logger.info("PPO model loaded from %s", path)
        except Exception as exc:
            logger.warning("Could not load PPO: %s", exc)

    def load_lstm(self, path: Path, n_features: int = 140) -> None:
        """Load LSTM-Attention checkpoint."""
        model = LSTMAttentionModel(n_features=n_features).to(self.device)
        state = torch.load(str(path), map_location=self.device)
        model.load_state_dict(state)
        model.eval()
        self.lstm_model = model
        logger.info("LSTM model loaded from %s", path)

    # ── Inference ───────────────────────────────────────────────────────────
    def predict(
        self,
        features: np.ndarray,
        seq: Optional[torch.Tensor] = None,
        regime_info: Optional[RegimeInfo] = None,
    ) -> Signal:
        """
        Generate a trading signal from input features.
        Returns a Signal object (direction, confidence, metadata).
        """
        votes: Dict[str, np.ndarray] = {}

        # PPO prediction
        if self._ppo_model is not None:
            action, _ = self._ppo_model.predict(features, deterministic=True)
            # action index should be aligned with ModelAction (0=HOLD, 1=BUY, 2=SELL)
            probs = np.zeros(3)
            probs[int(action)] = 1.0
            votes["ppo"] = probs

        # LSTM-Attention prediction
        if self.lstm_model is not None and seq is not None:
            with torch.no_grad():
                logits = self.lstm_model(seq.to(self.device).unsqueeze(0))
                probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]
            # Standardized: [HOLD, BUY, SELL]
            votes["lstm"] = probs

        # Cache confidences for calibration tracking
        for k, v in votes.items():
            self._last_confidences[k].append(float(np.max(v)))

        if not votes:
            logger.warning("No models loaded - returning HOLD")
            return Signal(direction=SignalDirection.HOLD, confidence=0.0, metadata={})

        # Weighted average across available models
        total_weight = sum(self.weights[k] for k in votes)
        blended = sum(self.weights[k] / total_weight * votes[k] for k in votes)
        action_idx = int(np.argmax(blended))
        confidence = float(blended[action_idx])

        # Map to standardized SignalDirection using ModelAction
        # ModelAction: 0=HOLD, 1=BUY, 2=SELL
        model_action = ModelAction(action_idx)
        direction = model_action.to_direction()

        per_algo = {k: float(np.argmax(votes[k])) for k in votes}
        logger.debug(
            "Ensemble | dir=%d conf=%.3f votes=%s",
            direction,
            confidence,
            per_algo,
        )
        return Signal(
            direction=direction,
            confidence=confidence,
            metadata={"per_algo_votes": per_algo, "weights": self.weights},
        )

    # ── Dynamic weight adaptation ────────────────────────────────────────────
    def record_return(
        self, algorithm: str, ret: float, regime_info: Optional[RegimeInfo] = None
    ) -> None:
        """Track per-algorithm returns for weight rebalancing."""
        if algorithm in self._performance:
            self._performance[algorithm].append(ret)
            if len(self._performance[algorithm]) >= 50:
                self._rebalance_weights(regime_info=regime_info)

    def _rebalance_weights(
        self, regime_info: Optional[RegimeInfo] = None, window: int = 50
    ) -> None:
        """Delegate rebalancing to DynamicEnsemble."""
        metrics: Dict[str, Dict[str, float]] = {}
        for algo, rets in self._performance.items():
            tail = list(rets)[-window:]
            if len(tail) < 10:
                metrics[algo] = {"accuracy": 0.5, "calibration_error": 0.0, "drift_score": 0.0}
                continue
            arr = np.array(tail)
            # Use Sharpe ratio as a proxy for 'accuracy' (0.5 baseline)
            mean = arr.mean()
            std = arr.std() + 1e-9
            sharpe = mean / std
            # Map Sharpe [-1, 1] to [0, 1] for accuracy input
            norm_accuracy = float(np.clip(0.5 + (sharpe * 0.2), 0.0, 1.0))

            # Calculate basic drift as recent performance degradation
            recent_mean = np.mean(tail[-10:])
            overall_mean = np.mean(tail)
            drift = float(
                np.clip((overall_mean - recent_mean) / (abs(overall_mean) + 1e-9), 0.0, 1.0)
            )

            # Calibration: Difference between avg confidence and actual success rate
            # Success is approximated as positive return
            success_rate = np.mean(arr > 0)
            conf_tail = list(self._last_confidences[algo])[-len(tail) :]
            if conf_tail:
                avg_conf = np.mean(conf_tail)
                cal_error = float(np.clip(abs(avg_conf - success_rate), 0.0, 1.0))
            else:
                cal_error = 0.0

            metrics[algo] = {
                "accuracy": norm_accuracy,
                "calibration_error": cal_error,
                "drift_score": drift,
            }

        self.dynamic_ensemble.update_weights(metrics, regime_info=regime_info)
        logger.info("Weights rebalanced: %s", self.weights)


__all__ = ["EnsembleModel", "LSTMAttentionModel"]
