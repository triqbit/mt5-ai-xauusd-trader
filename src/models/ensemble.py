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

import structlog
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn

from src.core.constants import SignalDirection
from src.models.dynamic_ensemble import DynamicEnsemble

logger = structlog.get_logger(__name__)


# ── LSTM + Attention sub-model ──────────────────────────────────────────────
class LSTMAttentionModel(nn.Module):
    """
    Bidirectional LSTM with multi-head self-attention.
    Input : (batch, seq_len, n_features)
    Output : (batch, 3) -> [buy_logit, sell_logit, hold_logit]
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


# ── Ensemble orchestrator ─────────────────────────────────────────────────
class EnsembleModel:
    """
    Weighted voting ensemble: PPO + Dreamer + LSTM-Attention.
    Delegates weight adaptation to DynamicEnsemble for robust rebalancing.
    """

    ALGORITHMS = ["ppo", "dreamer", "lstm"]

    def __init__(self, device: str = "cpu") -> None:
        self.device = torch.device(device)
        self.dynamic_ensemble = DynamicEnsemble(
            model_names=self.ALGORITHMS,
            smoothing_factor=0.1,
            max_swing=0.05,
            min_weight=0.05
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
            action, _ = self._ppo_model.predict(obs, deterministic=True)
            probs = np.zeros(3)
            probs[int(action)] = 1.0
            votes["ppo"] = probs

        # LSTM-Attention prediction
        if self.lstm_model is not None and seq is not None:
            with torch.no_grad():
                logits = self.lstm_model(seq.to(self.device).unsqueeze(0))
                probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]
            votes["lstm"] = probs

        if not votes:
            logger.warning("No models loaded - returning HOLD")
            return 0, 0.0, {}

        # Weighted average across available models
        total_weight = sum(self.weights[k] for k in votes)
        blended = sum(self.weights[k] / total_weight * votes[k] for k in votes)
        action_idx = int(np.argmax(blended))  # 0=buy, 1=sell, 2=hold (historic)
        confidence = float(blended[action_idx])

        # Map to standardized SignalDirection
        # Ensemble legacy used: 0=buy, 1=sell, 2=hold
        direction_map = {0: SignalDirection.BUY, 1: SignalDirection.SELL, 2: SignalDirection.HOLD}
        direction = direction_map[action_idx]

        per_algo = {k: float(np.argmax(votes[k])) for k in votes}
        logger.debug(
            "Ensemble prediction",
            direction=direction,
            confidence=confidence,
            votes=per_algo,
        )
        return direction, confidence, per_algo

    # ── Dynamic weight adaptation ────────────────────────────────────────────
    def record_return(self, algorithm: str, ret: float) -> None:
        """Track per-algorithm returns for weight rebalancing."""
        if algorithm in self._performance:
            self._performance[algorithm].append(ret)
            if len(self._performance[algorithm]) >= 50:
                self._rebalance_weights()

    def _rebalance_weights(self, window: int = 50) -> None:
        """Delegate rebalancing to DynamicEnsemble."""
        metrics: Dict[str, Dict[str, float]] = {}
        for algo, rets in self._performance.items():
            tail = rets[-window:]
            if len(tail) < 10:
                metrics[algo] = {"accuracy": 0.5}
                continue
            arr = np.array(tail)
            # Use Sharpe ratio as a proxy for 'accuracy' (0.5 baseline)
            mean = arr.mean()
            std = arr.std() + 1e-9
            sharpe = mean / std
            # Map Sharpe [-1, 1] to [0, 1] for accuracy input
            norm_accuracy = float(np.clip(0.5 + (sharpe * 0.2), 0.0, 1.0))
            metrics[algo] = {"accuracy": norm_accuracy}

        self.dynamic_ensemble.update_weights(metrics)
        logger.info("Weights rebalanced", weights=self.weights)


__all__ = ["EnsembleModel", "LSTMAttentionModel"]
