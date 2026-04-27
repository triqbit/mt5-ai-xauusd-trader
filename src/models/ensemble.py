"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/ensemble.py
Ensemble voting system combining:
  - PPO (Stable-Baselines3)
  - Dreamer V3 (world model RL)
  - LSTM + Multi-head Attention
Weighted confidence voting with consensus threshold and veto power.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
        """
        Initialize LSTM-Attention model.

        Args:
            n_features: Number of input features.
            hidden_size: Hidden size of LSTM.
            num_layers: Number of LSTM layers.
            n_heads: Number of attention heads.
            dropout: Dropout rate.
        """
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
        """
        Forward pass.

        Args:
            x: Input tensor (B, T, F).

        Returns:
            Output logits (B, 3).
        """
        out, _ = self.lstm(x)  # (B, T, 2*H)
        attn_out, _ = self.attn(out, out, out)
        out = self.norm(out + attn_out)  # residual
        pooled = out.mean(dim=1)  # global average pool
        return self.head(pooled)  # (B, 3)


# ── Ensemble orchestrator ─────────────────────────────────────────────────
class EnsembleModel:
    """
    Weighted voting ensemble: PPO + Dreamer + LSTM-Attention.
    Implements consensus thresholds and veto power from RISK_LIMITS.md.
    """

    ALGORITHMS = ["ppo", "dreamer", "lstm"]

    def __init__(
        self,
        device: str = "cpu",
        consensus_threshold: float = 0.60,
        veto_threshold: float = 0.40,
    ) -> None:
        """
        Initialize ensemble model.

        Args:
            device: Computing device ('cpu', 'cuda', etc.).
            consensus_threshold: Required agreement across ensemble.
            veto_threshold: Confidence below which a model vetoes a trade.
        """
        self.device = torch.device(device)
        self.weights: Dict[str, float] = {
            "ppo": 1 / 3,
            "dreamer": 1 / 3,
            "lstm": 1 / 3,
        }
        self.consensus_threshold = consensus_threshold
        self.veto_threshold = veto_threshold
        self._ppo_model = None  # loaded lazily
        self._dreamer_model = None  # loaded lazily
        self.lstm_model: Optional[LSTMAttentionModel] = None
        self._performance: Dict[str, List[float]] = {k: [] for k in self.ALGORITHMS}

    def load_ppo(self, path: Path) -> None:
        """
        Load a Stable-Baselines3 PPO checkpoint.

        Args:
            path: Path to the model file.
        """
        try:
            from stable_baselines3 import PPO

            self._ppo_model = PPO.load(str(path), device=self.device)
            logger.info("PPO model loaded from %s", path)
        except Exception as exc:
            logger.warning("Could not load PPO: %s", exc)

    def load_lstm(self, path: Path, n_features: int = 140) -> None:
        """
        Load LSTM-Attention checkpoint.

        Args:
            path: Path to the state_dict file.
            n_features: Number of features in input data.
        """
        try:
            model = LSTMAttentionModel(n_features=n_features).to(self.device)
            state = torch.load(str(path), map_location=self.device, weights_only=True)
            model.load_state_dict(state)
            model.eval()
            self.lstm_model = model
            logger.info("LSTM model loaded from %s", path)
        except Exception as e:
            logger.error("Failed to load LSTM model: %s", e)

    def predict(
        self,
        obs: np.ndarray,
        seq: Optional[torch.Tensor] = None,
    ) -> Tuple[int, float, Dict[str, float]]:
        """
        Return (direction, confidence, per_algo_probs).
        Implements Section 4.3 consensus and veto rules.

        Args:
            obs: Flattened observation vector.
            seq: Optional sequential data for LSTM.

        Returns:
            Tuple of (direction, confidence, per_algo_choices).
            direction: +1 buy, -1 sell, 0 hold.
        """
        votes: Dict[str, np.ndarray] = {}

        # 1. Gather predictions from all available sub-models
        if self._ppo_model is not None:
            action, _ = self._ppo_model.predict(obs, deterministic=True)
            # direction_map aligns with main.py: 0: 1 (Buy), 1: -1 (Sell), 2: 0 (Hold)
            probs = np.zeros(3)
            probs[int(action)] = 1.0
            votes["ppo"] = probs

        if self.lstm_model is not None and seq is not None:
            with torch.no_grad():
                logits = self.lstm_model(seq.to(self.device).unsqueeze(0))
                probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]
            votes["lstm"] = probs

        # 2. Handle empty ensemble
        if not votes:
            logger.warning("No models loaded - returning HOLD")
            return 0, 0.0, {}

        # 3. Check for Veto Power (Section 4.3)
        for algo, probs in votes.items():
            max_conf = np.max(probs)
            if max_conf < self.veto_threshold:
                logger.info(
                    "Veto triggered by %s (confidence %.2f < %.2f)",
                    algo,
                    max_conf,
                    self.veto_threshold,
                )
                return 0, max_conf, {k: float(np.argmax(v)) for k, v in votes.items()}

        # 4. Consensus Check (Section 4.3)
        total_weight = sum(self.weights[k] for k in votes)
        blended = sum(self.weights[k] / total_weight * votes[k] for k in votes)

        action_idx = int(np.argmax(blended))
        confidence = float(blended[action_idx])

        if confidence < self.consensus_threshold:
            logger.info(
                "Consensus NOT reached (%.2f < %.2f)",
                confidence,
                self.consensus_threshold,
            )
            return 0, confidence, {k: float(np.argmax(v)) for k, v in votes.items()}

        # 5. Map action to trade direction
        direction_map = {0: 1, 1: -1, 2: 0}
        direction = direction_map[action_idx]

        per_algo = {k: float(np.argmax(votes[k])) for k in votes}
        logger.debug(
            "Ensemble | dir=%d conf=%.3f votes=%s", direction, confidence, per_algo
        )

        return direction, confidence, per_algo

    def record_return(self, algorithm: str, ret: float) -> None:
        """Track per-algorithm returns for weight rebalancing."""
        if algorithm in self._performance:
            self._performance[algorithm].append(ret)
            if len(self._performance[algorithm]) >= 50:
                self._rebalance_weights()

    def _rebalance_weights(self, window: int = 50) -> None:
        """Reweight by rolling Sharpe ratio (floor 5%)."""
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
        for algo, s in sharpes.items():
            raw = s / total
            self.weights[algo] = max(raw, 0.05)  # min 5%

        # Normalise
        total_w = sum(self.weights.values())
        self.weights = {k: v / total_w for k, v in self.weights.items()}
        logger.info("Weights rebalanced: %s", self.weights)


__all__ = ["EnsembleModel", "LSTMAttentionModel"]
