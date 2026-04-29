"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/lstm_model.py
LSTM sequence model using PyTorch for short-term price prediction.
"""

import logging
from typing import Optional

import numpy as np

from src.models.base import BaseModel, Signal

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    nn = object  # type: ignore


class LSTMModel(BaseModel, nn.Module if TORCH_AVAILABLE else object):  # type: ignore
    """
    LSTM model for predicting price direction from sequences of market data.
    """

    def __init__(
        self,
        input_dim: int = 140,
        hidden_dim: int = 64,
        num_layers: int = 2,
        output_dim: int = 3,
    ):
        """
        Initialise LSTM Model.

        Args:
            input_dim: Number of input features.
            hidden_dim: Number of LSTM hidden units.
            num_layers: Number of LSTM layers.
            output_dim: Number of output classes (Buy, Sell, Hold).
        """
        if TORCH_AVAILABLE:
            nn.Module.__init__(self)
            self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True)
            self.fc = nn.Linear(hidden_dim, output_dim)
        else:
            logging.warning("PyTorch not installed. LSTMModel restricted.")

    def forward(self, x: "torch.Tensor") -> "torch.Tensor":
        """Forward pass."""
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not installed.")
        out, _ = self.lstm(x)
        out = self.fc(out[:, -1, :])
        return out

    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading action from the input features.

        Args:
            features: Input features for the model.

        Returns:
            Signal: direction (1=Buy, -1=Sell, 0=Hold) and confidence.
        """
        if not TORCH_AVAILABLE:
            return Signal(direction=0, confidence=0.0)

        self.eval()
        with torch.no_grad():
            # Convert features to torch tensor and ensure correct shape (B, T, F)
            if features.ndim == 2:
                features = np.expand_dims(features, axis=0)

            x = torch.from_numpy(features).float()
            logits = self.forward(x)
            probs = torch.softmax(logits, dim=-1)

            # Map action: 0=Hold, 1=Buy, 2=Sell
            action_idx = torch.argmax(probs, dim=-1).item()
            confidence = float(probs[0, action_idx].item())

            direction_map = {0: 0, 1: 1, 2: -1}
            direction = direction_map.get(action_idx, 0)

            return Signal(direction=direction, confidence=confidence)
