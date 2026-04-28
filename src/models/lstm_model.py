"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/lstm_model.py
LSTM sequence model for short-term price prediction using PyTorch.
"""

import logging
from typing import Optional

import numpy as np
import torch
import torch.nn as nn

from .base import BaseModel, Signal

logger = logging.getLogger(__name__)


class LSTMModel(nn.Module, BaseModel):
    """
    LSTM-based sequence model for market prediction.
    Input shape: (batch, seq_len, n_features)
    Output: Signal (Buy/Sell/Hold)
    """

    def __init__(
        self,
        input_dim: int = 64,
        hidden_dim: int = 128,
        num_layers: int = 2,
        output_dim: int = 3,
        dropout: float = 0.2,
    ):
        super(LSTMModel, self).__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers

        self.lstm = nn.LSTM(
            input_dim,
            hidden_dim,
            num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.fc = nn.Linear(hidden_dim, output_dim)
        self.softmax = nn.Softmax(dim=-1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass of the model.
        Args:
            x: Input tensor of shape (batch, seq_len, input_dim)
        Returns:
            Output tensor of shape (batch, output_dim)
        """
        # Initialize hidden state with zeros
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)

        # Forward propagate LSTM
        out, _ = self.lstm(x, (h0, c0))

        # Decode the hidden state of the last time step
        out = self.fc(out[:, -1, :])
        return out

    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading signal from input features.
        Args:
            features: Market data features, expected shape (seq_len, input_dim)
                     or (batch, seq_len, input_dim).
        Returns:
            Signal: The generated trading signal.
        """
        self.eval()
        with torch.no_grad():
            # Convert numpy array to torch tensor
            x = torch.from_numpy(features).float()

            # Add batch dimension if missing
            if x.ndim == 2:
                x = x.unsqueeze(0)

            logits = self.forward(x)
            probs = self.softmax(logits).cpu().numpy()[0]

            # Action mapping: 0=Hold, 1=Buy, 2=Sell (to match gym env)
            # Map index to direction: 0->0, 1->1, 2->-1
            action_idx = np.argmax(probs)
            confidence = float(probs[action_idx])

            mapping = {0: 0, 1: 1, 2: -1}
            direction = mapping.get(action_idx, 0)

            return Signal(direction=direction, confidence=confidence)

    def save(self, path: str):
        """Save model weights."""
        torch.save(self.state_dict(), path)
        logger.info("Model saved to %s", path)

    def load(self, path: str):
        """Load model weights."""
        self.load_state_dict(torch.load(path))
        self.eval()
        logger.info("Model loaded from %s", path)
