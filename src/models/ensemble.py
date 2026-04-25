"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/ensemble.py
Ensemble voting system combining:
  - PPO (Stable-Baselines3)
  - Dreamer V3 (world model RL)
  - LSTM + Multi-head Attention
Performance-weighted consensus voting.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    # Define dummy classes to avoid NameError if torch is missing in CI
    class nn:
        class Module:
            pass

logger = logging.getLogger(__name__)


# ── LSTM + Attention sub-model ──────────────────────────────────────────────
class LSTMAttentionModel(nn.Module if TORCH_AVAILABLE else object):
    """
    Bidirectional LSTM with multi-head self-attention.
    Input : (batch, seq_len, n_features)
    Output : (batch, 3) -> [hold_logit, buy_logit, sell_logit]
    Note: Standardizing mapping: 0=Hold, 1=Buy, 2=Sell
    """

    def __init__(
        self,
        n_features: int = 140,
        hidden_size: int = 128,
        num_layers: int = 2,
        n_heads: int = 8,
        dropout: float = 0.2,
    ) -> None:
        if not TORCH_AVAILABLE:
            raise ImportError("torch is required for LSTMAttentionModel")
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
    Weights are performance-weighted based on Sharpe ratio.
    """

    ALGORITHMS = ["ppo", "dreamer", "lstm"]

    def __init__(self, device: str = "cpu") -> None:
        if TORCH_AVAILABLE:
            self.device = torch.device(device)
        else:
            self.device = None
        self.weights: Dict[str, float] = {
            "ppo": 1 / 3,
            "dreamer": 1 / 3,
            "lstm": 1 / 3,
        }
        self._ppo_model = None
        self._dreamer_model = None
        self.lstm_model: Optional[LSTMAttentionModel] = None
        self._performance: Dict[str, List[float]] = {k: [] for k in self.ALGORITHMS}

    def load_ppo(self, path: Path) -> None:
        try:
            from stable_baselines3 import PPO
            self._ppo_model = PPO.load(str(path), device=self.device)
            logger.info("PPO model loaded.")
        except Exception as exc:
            logger.warning("Could not load PPO: %s", exc)

    def load_lstm(self, path: Path, n_features: int = 140) -> None:
        if not TORCH_AVAILABLE:
            logger.warning("torch not available - cannot load LSTM")
            return
        model = LSTMAttentionModel(n_features=n_features).to(self.device)
        state = torch.load(str(path), map_location=self.device)
        model.load_state_dict(state)
        model.eval()
        self.lstm_model = model
        logger.info("LSTM model loaded.")

    def predict(
        self,
        obs: np.ndarray,
        seq: Optional[Any] = None,
    ) -> Tuple[int, float, Dict[str, float]]:
        """
        Return (direction, confidence, per_algo_probs).
        direction: +1 buy, -1 sell, 0 hold
        Action mapping: 0=Hold, 1=Buy, 2=Sell
        """
        votes: Dict[str, np.ndarray] = {}

        if self._ppo_model is not None:
            action, _ = self._ppo_model.predict(obs, deterministic=True)
            probs = np.zeros(3)
            probs[int(action)] = 1.0
            votes["ppo"] = probs

        if TORCH_AVAILABLE and self.lstm_model is not None and seq is not None:
            with torch.no_grad():
                logits = self.lstm_model(seq.to(self.device).unsqueeze(0))
                probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]
            votes["lstm"] = probs

        if not votes:
            return 0, 0.0, {}

        # Weighted consensus
        total_weight = sum(self.weights[k] for k in votes)
        blended = sum(self.weights[k] / total_weight * votes[k] for k in votes)

        action_idx = int(np.argmax(blended))
        confidence = float(blended[action_idx])

        # Mapping: 0=Hold, 1=Buy, 2=Sell -> Direction: 0, 1, -1
        direction_map = {0: 0, 1: 1, 2: -1}
        direction = direction_map[action_idx]

        per_algo = {k: float(np.argmax(votes[k])) for k in votes}
        return direction, confidence, per_algo

    def record_return(self, algorithm: str, ret: float) -> None:
        if algorithm in self._performance:
            self._performance[algorithm].append(ret)
            if len(self._performance[algorithm]) >= 50:
                self._rebalance_weights()

    def _rebalance_weights(self) -> None:
        sharpes: Dict[str, float] = {}
        for algo, rets in self._performance.items():
            if len(rets) < 10:
                sharpes[algo] = 1.0
                continue
            arr = np.array(rets[-50:])
            sharpes[algo] = max(arr.mean() / (arr.std() + 1e-9), 0.0)

        total = sum(sharpes.values()) or 1.0
        for algo in self.ALGORITHMS:
            self.weights[algo] = max(sharpes.get(algo, 0.0) / total, 0.05)

        total_w = sum(self.weights.values())
        self.weights = {k: v / total_w for k, v in self.weights.items()}


__all__ = ["EnsembleModel", "LSTMAttentionModel"]
