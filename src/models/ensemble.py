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
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


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
    Weights are initialised equally and adapt based on a rolling window
    of each algorithm's realised P&L Sharpe ratio.
    """

    ALGORITHMS = ["ppo", "dreamer", "lstm"]

    def __init__(self, device: str = "cpu") -> None:
        """Initialize the ensemble model."""
        self.device = torch.device(
            device if torch.cuda.is_available() or device != "cuda" else "cpu"
        )
        self.weights: Dict[str, float] = {
            "ppo": 1 / 3,
            "dreamer": 1 / 3,
            "lstm": 1 / 3,
        }
        self._ppo_model: Optional[Any] = None  # loaded lazily
        self._dreamer_model: Optional[Any] = None  # loaded lazily
        self.lstm_model: Optional[LSTMAttentionModel] = None
        self._performance: Dict[str, List[float]] = {k: [] for k in self.ALGORITHMS}

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
        Aggregate predictions from all loaded models.

        Args:
            obs: Flat observation vector for RL models.
            seq: Sequence tensor for LSTM (batch, seq_len, features).

        Returns:
            Tuple of (direction, confidence, per_algo_probs).
            direction: +1 buy, -1 sell, 0 hold.
            confidence: Weighted probability of the chosen direction.
            per_algo_probs: Raw output index from each model.
        """
        votes: Dict[str, np.ndarray] = {}

        # 1. PPO Prediction
        if self._ppo_model is not None:
            try:
                action, _ = self._ppo_model.predict(obs, deterministic=True)
                probs = np.zeros(3)
                probs[int(action)] = 1.0
                votes["ppo"] = probs
            except Exception as e:
                logger.error("PPO prediction failed: %s", e)

        # 2. LSTM-Attention Prediction
        if self.lstm_model is not None and seq is not None:
            try:
                with torch.no_grad():
                    # Ensure seq has batch dimension
                    if seq.dim() == 2:
                        seq = seq.unsqueeze(0)
                    logits = self.lstm_model(seq.to(self.device))
                    probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]
                votes["lstm"] = probs
            except Exception as e:
                logger.error("LSTM prediction failed: %s", e)

        # 3. Dreamer Prediction (Placeholder)
        if self._dreamer_model is not None:
            # Implement Dreamer V3 inference here
            pass

        if not votes:
            logger.warning("No models loaded or all predictions failed - returning HOLD")
            return 0, 0.0, {}

        # Weighted average across available models
        total_weight = sum(self.weights[k] for k in votes)
        if total_weight == 0:
            return 0, 0.0, {}

        blended = sum(self.weights[k] / total_weight * votes[k] for k in votes)

        # Mapping: 0=Buy, 1=Sell, 2=Hold (StableBaselines/Gym standard often differs,
        # but let's stick to the convention defined in this project's ensemble)
        # Assuming internal convention: 0=Buy, 1=Sell, 2=Hold
        action_idx = int(np.argmax(blended))
        confidence = float(blended[action_idx])

        direction_map = {0: 1, 1: -1, 2: 0}
        direction = direction_map[action_idx]

        per_algo = {k: float(np.argmax(votes[k])) for k in votes}

        logger.debug(
            "Ensemble | dir=%d conf=%.3f votes=%s",
            direction,
            confidence,
            per_algo,
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
        """Reweight models by rolling Sharpe ratio."""
        sharpes: Dict[str, float] = {}
        for algo, rets in self._performance.items():
            tail = rets[-window:]
            if len(tail) < 10:
                sharpes[algo] = 1.0
                continue
            arr = np.array(tail)
            mean = arr.mean()
            std = arr.std() + 1e-9
            sharpes[algo] = max(mean / std, 0.0)

        total = sum(sharpes.values()) or 1.0
        for algo in self.ALGORITHMS:
            s = sharpes.get(algo, 0.0)
            raw = s / total
            self.weights[algo] = max(raw, 0.05)  # min 5% floor

        # Re-normalise
        total_w = sum(self.weights.values())
        self.weights = {k: v / total_w for k, v in self.weights.items()}
        logger.info("Ensemble weights rebalanced: %s", self.weights)


__all__ = ["EnsembleModel", "LSTMAttentionModel"]
