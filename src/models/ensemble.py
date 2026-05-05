"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/ensemble.py
Ensemble voting system combining signals from multiple AI models:
  - PPO (Stable-Baselines3)
  - Dreamer V3 (world model RL)
  - LSTM + Multi-head Attention
Weighted confidence voting with model dissent checks and dynamic weight adaptation.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from collections import deque
from pathlib import Path
from typing import Any, Dict

import numpy as np

try:
    import torch
    import torch.nn as nn
except ImportError:
    torch = None  # type: ignore
    nn = None  # type: ignore

from src.core.constants import ModelAction, SignalDirection
from src.core.profiler import profile
from src.models.base_model import BaseModel, Signal
from src.models.dynamic_ensemble import DynamicEnsemble
from src.models.lstm_model import LSTMAttentionModel
from src.models.regime_detector import RegimeInfo

logger = logging.getLogger(__name__)


# ── Ensemble orchestrator ─────────────────────────────────────────────────
class EnsembleModel(BaseModel):
    """
    Weighted voting ensemble: PPO + Dreamer + LSTM-Attention.
    Delegates weight adaptation to DynamicEnsemble for robust rebalancing.
    Implements institutional consensus (60%) and dissent checks.
    """

    ALGORITHMS = ["ppo", "dreamer", "lstm"]

    def __init__(
        self,
        device: str = "cpu",
        consensus_threshold: float = 0.60,
        model_weights: Dict[str, float] | None = None,
    ) -> None:
        super().__init__()
        self.device = torch.device(device) if torch is not None else None
        self.dynamic_ensemble = DynamicEnsemble(
            model_names=self.ALGORITHMS, smoothing_factor=0.1, max_swing=0.05, min_weight=0.05
        )
        if model_weights:
            # Overwrite initial weights if provided
            # Standardize weights to sum to 1.0
            total = sum(model_weights.values())
            self.dynamic_ensemble.weights = {k: v / total for k, v in model_weights.items()}

        self._ppo_model = None  # loaded lazily
        self._dreamer_model = None  # loaded lazily
        self.lstm_model: LSTMAttentionModel | None = None
        self.consensus_threshold = consensus_threshold

        self._performance: dict[str, deque[float]] = {k: deque(maxlen=200) for k in self.ALGORITHMS}
        self._last_confidences: dict[str, deque[float]] = {
            k: deque(maxlen=200) for k in self.ALGORITHMS
        }
        self._latest_health_metrics: dict[str, float] = {
            "accuracy": 1.0,
            "drift": 0.0,
            "calibration": 0.0,
        }

    @property
    def weights(self) -> dict[str, float]:
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
        if torch is None:
            logger.warning("PyTorch not found. Cannot load LSTM.")
            return
        model = LSTMAttentionModel(n_features=n_features).to(self.device)
        state = torch.load(str(path), map_location=self.device, weights_only=True)
        model.load_state_dict(state)
        model.eval()
        self.lstm_model = model
        logger.info("LSTM model loaded from %s", path)

    # ── Inference ───────────────────────────────────────────────────────────
    def predict(
        self,
        features: np.ndarray,
        seq: Any | None = None,
        regime_info: RegimeInfo | None = None,
    ) -> Signal:
        """
        Generate a trading signal from input features using a weighted ensemble of models.

        Args:
            features (np.ndarray): Input feature vector for model inference.
            seq (Optional[Any]): Sequence data for LSTM models.
            regime_info (Optional[RegimeInfo]): Current market regime information.

        Returns:
            Signal: The aggregated ensemble signal (BUY, SELL, or HOLD).
        """
        votes: dict[str, np.ndarray] = {}

        # 1. PPO prediction
        if self._ppo_model is not None:
            with profile("inference_ppo"):
                action, _ = self._ppo_model.predict(features, deterministic=True)
                # action: 0=HOLD, 1=BUY, 2=SELL (ModelAction mapping)
                probs = np.zeros(3)
                probs[int(action)] = 1.0
                votes["ppo"] = probs

        # 2. LSTM-Attention prediction
        if self.lstm_model is not None and seq is not None and torch is not None:
            with profile("inference_lstm"):
                with torch.no_grad():
                    # Expected input: [batch, seq_len, features]
                    logits = self.lstm_model(seq.to(self.device).unsqueeze(0))
                    probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]
                votes["lstm"] = probs

        # TODO: Add Dreamer V3 prediction path when integrated

        if not votes:
            logger.warning("No models loaded - returning HOLD")
            return Signal(direction=SignalDirection.HOLD, confidence=0.0)

        # Cache confidences for calibration tracking
        for k, v in votes.items():
            self._last_confidences[k].append(float(np.max(v)))

        # 3. Model Consensus & Dissent Check
        model_signals: Dict[str, Signal] = {}
        for name, probs in votes.items():
            action_idx = int(np.argmax(probs))
            conf = float(probs[action_idx])
            direction = ModelAction(action_idx).to_direction()
            model_signals[name] = Signal(direction=direction, confidence=conf)

        # Dissent Check: Block if there are conflicting BUY and SELL signals
        has_buy = any(s.direction == SignalDirection.BUY for s in model_signals.values())
        has_sell = any(s.direction == SignalDirection.SELL for s in model_signals.values())

        if has_buy and has_sell:
            logger.warning("Dissent detected: BUY and SELL conflict. Returning HOLD.")
            return Signal(
                direction=SignalDirection.HOLD,
                confidence=0.0,
                metadata={
                    "reason": "Dissent conflict",
                    "model_signals": {
                        k: {"dir": s.direction.name, "conf": s.confidence}
                        for k, s in model_signals.items()
                    },
                },
            )

        # 4. Weighted Aggregation
        # Normalize weights for the models that actually voted
        total_active_weight = sum(self.weights.get(k, 0.0) for k in votes)
        if total_active_weight <= 0:
            logger.error("Total active weight is zero.")
            return Signal(direction=SignalDirection.HOLD, confidence=0.0)

        blended_probs = np.zeros(3)
        for name, probs in votes.items():
            weight = self.weights.get(name, 0.0) / total_active_weight
            blended_probs += weight * probs

        # 5. Threshold Validation
        # blended_probs order: [HOLD, BUY, SELL] per ModelAction indices
        buy_conf = blended_probs[int(ModelAction.BUY)]
        sell_conf = blended_probs[int(ModelAction.SELL)]
        hold_conf = blended_probs[int(ModelAction.HOLD)]

        if buy_conf >= self.consensus_threshold:
            final_direction = SignalDirection.BUY
            final_confidence = buy_conf
        elif sell_conf >= self.consensus_threshold:
            final_direction = SignalDirection.SELL
            final_confidence = sell_conf
        else:
            final_direction = SignalDirection.HOLD
            final_confidence = hold_conf

        logger.info(
            "Ensemble Result | Dir: %s | Conf: %.2f | Active Algos: %s",
            final_direction,
            final_confidence,
            list(votes.keys()),
        )

        return Signal(
            direction=final_direction,
            confidence=final_confidence,
            metadata={
                "weighted_probs": {
                    "BUY": buy_conf,
                    "SELL": sell_conf,
                    "HOLD": hold_conf,
                },
                "weights": self.weights,
                "model_signals": {
                    k: {"dir": s.direction.name, "conf": s.confidence}
                    for k, s in model_signals.items()
                },
            },
        )

    def aggregate_signals(self, signals: Dict[str, Signal]) -> Signal:
        """
        Manually aggregate pre-calculated signals using weighted consensus.
        """
        if not signals:
            return Signal(direction=SignalDirection.HOLD, confidence=0.0)

        has_buy = any(s.direction == SignalDirection.BUY for s in signals.values())
        has_sell = any(s.direction == SignalDirection.SELL for s in signals.values())

        if has_buy and has_sell:
            return Signal(
                direction=SignalDirection.HOLD,
                confidence=0.0,
                metadata={
                    "reason": "Dissent conflict",
                    "model_signals": {
                        k: {"dir": s.direction.name, "conf": s.confidence}
                        for k, s in signals.items()
                    },
                },
            )

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

        if weighted_buy_conf >= self.consensus_threshold:
            return Signal(direction=SignalDirection.BUY, confidence=weighted_buy_conf)
        elif weighted_sell_conf >= self.consensus_threshold:
            return Signal(direction=SignalDirection.SELL, confidence=weighted_sell_conf)
        else:
            return Signal(direction=SignalDirection.HOLD, confidence=weighted_hold_conf)

    # ── Dynamic weight adaptation ────────────────────────────────────────────
    def record_return(
        self, algorithm: str, ret: float, regime_info: RegimeInfo | None = None
    ) -> None:
        """Track per-algorithm returns for weight rebalancing."""
        if algorithm in self._performance:
            self._performance[algorithm].append(ret)
            if len(self._performance[algorithm]) >= 50:
                self._rebalance_weights(regime_info=regime_info)

    def _rebalance_weights(self, regime_info: RegimeInfo | None = None, window: int = 50) -> None:
        """Delegate rebalancing to DynamicEnsemble."""
        metrics: dict[str, dict[str, float]] = {}
        for algo, rets in self._performance.items():
            tail = list(rets)[-window:]
            if len(tail) < 10:
                metrics[algo] = {"accuracy": 0.5, "calibration_error": 0.0, "drift_score": 0.0}
                continue
            arr = np.array(tail)
            mean = arr.mean()
            std = arr.std() + 1e-9
            sharpe = mean / std
            norm_accuracy = float(np.clip(0.5 + (sharpe * 0.2), 0.0, 1.0))

            recent_mean = np.mean(tail[-10:])
            overall_mean = np.mean(tail)
            drift = float(
                np.clip((overall_mean - recent_mean) / (abs(overall_mean) + 1e-9), 0.0, 1.0)
            )

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

        current_weights = self.weights
        agg_acc = 0.0
        agg_drift = 0.0
        agg_cal = 0.0
        for algo, m in metrics.items():
            w = current_weights.get(algo, 0.0)
            agg_acc += w * m["accuracy"]
            agg_drift += w * m["drift_score"]
            agg_cal += w * m["calibration_error"]

        self._latest_health_metrics = {
            "accuracy": agg_acc,
            "drift": agg_drift,
            "calibration": agg_cal,
        }

        logger.info(
            "Weights rebalanced: %s | Agg Health: acc=%.2f drift=%.2f",
            self.weights,
            agg_acc,
            agg_drift,
        )

    def get_health_metrics(self) -> dict[str, float]:
        """Expose latest aggregate health metrics."""
        return self._latest_health_metrics.copy()


__all__ = ["EnsembleModel"]
