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
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.core.constants import SignalDirection
from src.models.dynamic_ensemble import DynamicEnsemble

logger = logging.getLogger(__name__)

# Defensive imports for heavy AI dependencies
try:
    import torch
    import torch.nn as nn

    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    nn = None
    TORCH_AVAILABLE = False


# ── LSTM + Attention sub-model ──────────────────────────────────────────────
if TORCH_AVAILABLE:

    class LSTMAttentionModel(nn.Module):
        """
        Bidirectional LSTM with multi-head self-attention.
        Input : (batch, seq_len, n_features)
        Output : (batch, 3) -> [hold_logit, buy_logit, sell_logit]
        """

        def __init__(
            self,
            n_features: int = 140,
            hidden_size: int = 128,
            num_layers: int = 2,
            n_heads: int = 8,
            dropout: float = 0.2,
        ) -> None:
            super().__init__()
            self.lstm = nn.LSTM(
                input_size=n_features,
                hidden_size=hidden_size,
                num_layers=num_layers,
                batch_first=True,
                bidirectional=True,
                dropout=dropout if num_layers > 1 else 0.0,
            )
            self.attn = nn.MultiheadAttention(
                embed_dim=hidden_size * 2,
                num_heads=n_heads,
                dropout=dropout,
                batch_first=True,
            )
            self.norm = nn.LayerNorm(hidden_size * 2)
            self.head = nn.Sequential(
                nn.Linear(hidden_size * 2, 64),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(64, 3),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            out, _ = self.lstm(x)  # (B, T, 2*H)
            attn_out, _ = self.attn(out, out, out)
            out = self.norm(out + attn_out)  # residual
            pooled = out.mean(dim=1)  # global average pool
            return self.head(pooled)  # (B, 3)
else:

    class LSTMAttentionModel:
        def __init__(self, *args, **kwargs):
            pass


# ── Ensemble orchestrator ─────────────────────────────────────────────────
class EnsembleModel:
    """
    Weighted voting ensemble: PPO + Dreamer + LSTM-Attention.
    Delegates weight adaptation to DynamicEnsemble for robust rebalancing.
    """

    ALGORITHMS = ["ppo", "dreamer", "lstm"]

    def __init__(self, device: str = "cpu", consensus_threshold: float = 0.60) -> None:
        self.device_str = device
        if TORCH_AVAILABLE:
            self.device = torch.device(device)
        self.consensus_threshold = consensus_threshold
        self.dynamic_ensemble = DynamicEnsemble(
            model_names=self.ALGORITHMS, smoothing_factor=0.1, max_swing=0.05, min_weight=0.05
        )
        self._ppo_model = None  # loaded lazily
        self._dreamer_model = None  # loaded lazily
        self.lstm_model: Optional[LSTMAttentionModel] = None
        # Internal cache for compatibility with existing record_return calls
        self._performance: Dict[str, List[float]] = {k: [] for k in self.ALGORITHMS}

    @property
    def weights(self) -> Dict[str, float]:
        """Expose weights from dynamic_ensemble."""
        return self.dynamic_ensemble.get_weights()

    # ── Loading ────────────────────────────────────────────────────────────
    def load_ppo(self, path: Path) -> None:
        """Load a Stable-Baselines3 PPO checkpoint."""
        try:
            from stable_baselines3 import PPO

            self._ppo_model = PPO.load(
                str(path), device=self.device_str if not TORCH_AVAILABLE else self.device
            )
            logger.info("PPO model loaded from %s", path)
        except Exception as exc:
            logger.warning("Could not load PPO: %s", exc)

    def load_lstm(self, path: Path, n_features: int = 140) -> None:
        """Load LSTM-Attention checkpoint."""
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch not available - cannot load LSTM.")
            return
        try:
            model = LSTMAttentionModel(n_features=n_features).to(self.device)
            state = torch.load(str(path), map_location=self.device)
            model.load_state_dict(state)
            model.eval()
            self.lstm_model = model
            logger.info("LSTM model loaded from %s", path)
        except Exception as exc:
            logger.warning("Could not load LSTM: %s", exc)

    # ── Inference ───────────────────────────────────────────────────────────
    def predict(
        self,
        obs: np.ndarray,
        seq: Optional[torch.Tensor] = None,
    ) -> Tuple[int, float, Dict[str, float]]:
        """
        Return (direction, confidence, per_algo_probs).
        direction: +1 buy, -1 sell, 0 hold
        """
        votes: Dict[str, np.ndarray] = {}

        # PPO prediction
        if self._ppo_model is not None:
            # Action mapping: 0=HOLD, 1=BUY, 2=SELL (ModelAction standard)
            action, _ = self._ppo_model.predict(obs, deterministic=True)
            probs = np.zeros(3)
            probs[int(action)] = 1.0
            votes["ppo"] = probs

        # LSTM-Attention prediction
        if TORCH_AVAILABLE and self.lstm_model is not None and seq is not None:
            with torch.no_grad():
                if seq.ndim == 2:
                    seq = seq.unsqueeze(0)
                logits = self.lstm_model(seq.to(self.device))
                probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]
            votes["lstm"] = probs

        if not votes:
            return SignalDirection.HOLD, 0.0, {}

        # Weighted average across available models
        total_weight = sum(self.weights[k] for k in votes)
        if total_weight == 0:
            return SignalDirection.HOLD, 0.0, {}

        blended = sum(self.weights[k] / total_weight * votes[k] for k in votes)

        # Probs mapping: 0=HOLD, 1=BUY, 2=SELL
        action_idx = int(np.argmax(blended))
        confidence = float(blended[action_idx])

        # Consensus gate
        if confidence < self.consensus_threshold:
            return (
                SignalDirection.HOLD,
                confidence,
                {k: float(np.argmax(v)) for k, v in votes.items()},
            )

        direction_map = {0: SignalDirection.HOLD, 1: SignalDirection.BUY, 2: SignalDirection.SELL}
        direction = direction_map[action_idx]

        per_algo = {k: float(np.argmax(v)) for k, v in votes.items()}
        return direction, confidence, per_algo

    # ── Dynamic weight adaptation ────────────────────────────────────────────
    def record_return(self, algorithm: str, ret: float) -> None:
        if algorithm in self._performance:
            self._performance[algorithm].append(ret)
            if len(self._performance[algorithm]) >= 50:
                self._rebalance_weights()

    def _rebalance_weights(self, window: int = 50) -> None:
        metrics: Dict[str, Dict[str, float]] = {}
        for algo, rets in self._performance.items():
            tail = rets[-window:]
            if len(tail) < 10:
                metrics[algo] = {"accuracy": 0.5}
                continue
            arr = np.array(tail)
            mean = arr.mean()
            std = arr.std() + 1e-9
            sharpe = mean / std
            norm_accuracy = float(np.clip(0.5 + (sharpe * 0.2), 0.0, 1.0))
            metrics[algo] = {"accuracy": norm_accuracy}

        self.dynamic_ensemble.update_weights(metrics)


__all__ = ["EnsembleModel", "LSTMAttentionModel"]
