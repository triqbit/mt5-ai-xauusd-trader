"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/lstm_model.py
LSTM sequence model using PyTorch for short-term price prediction.
"""

import logging
from typing import Optional

import numpy as np
import torch
import torch.nn as nn

from src.models.base import BaseModel, Signal

logger = logging.getLogger(__name__)


class PriceLSTM(nn.Module):
    """
    PyTorch LSTM architecture for price sequence classification.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 64,
        num_layers: int = 2,
        output_dim: int = 3,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.lstm = nn.LSTM(
            input_dim,
            hidden_dim,
            num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
        )
        self.fc = nn.Linear(hidden_dim, output_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (batch, seq_len, input_dim)
        out, _ = self.lstm(x)
        # Take the output of the last time step
        out = self.fc(out[:, -1, :])
        return out


class LSTMModel(BaseModel):
    """
    LSTM-based trading model.
    """

    def __init__(
        self,
        input_dim: int = 140,
        hidden_dim: int = 64,
        num_layers: int = 2,
        device: str = "cpu",
    ):
        """
        Initialise LSTM model.
        """
        self.device = torch.device(device)
        self.model = PriceLSTM(input_dim, hidden_dim, num_layers).to(self.device)
        self.model.eval()

    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading signal from sequence features.

        Args:
            features: Input features of shape (seq_len, input_dim) or (batch, seq_len, input_dim).

        Returns:
            Signal: direction (+1 buy, -1 sell, 0 hold) and confidence.
        """
        # Ensure features is a torch tensor with batch dimension
        if features.ndim == 2:
            x = torch.from_numpy(features).unsqueeze(0).float().to(self.device)
        else:
            x = torch.from_numpy(features).float().to(self.device)

        with torch.no_grad():
            logits = self.model(x)
            probs = torch.softmax(logits, dim=-1)
            # Take the first batch element if multiple
            prob_dist = probs[0].cpu().numpy()

        action_idx = np.argmax(prob_dist)
        confidence = float(prob_dist[action_idx])

        # Mapping: 0=Buy, 1=Sell, 2=Hold (matching EnsembleModel logic)
        action_map = {0: 1, 1: -1, 2: 0}
        direction = action_map.get(int(action_idx), 0)

        return Signal(direction=direction, confidence=confidence)

    def load_state_dict(self, path: str):
        """Load model weights."""
        self.model.load_state_dict(torch.load(path, map_location=self.device))
        self.model.eval()
