"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/lstm_model.py
LSTM sequence model for price prediction and signal generation.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import torch
import torch.nn as nn

from src.models.base import BaseModel, Signal

logger = logging.getLogger(__name__)


class LSTMNet(nn.Module):
    """
    PyTorch LSTM network for sequence classification.
    Input: (batch, seq_len, n_features)
    Output: (batch, 3) -> [Hold, Buy, Sell]
    """

    def __init__(
        self,
        input_size: int = 140,
        hidden_size: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.fc = nn.Linear(hidden_size, 3)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, T, F)
        out, _ = self.lstm(x)
        # Take the last time step
        out = out[:, -1, :]
        return self.fc(out)


class LSTMModel(BaseModel):
    """
    LSTM-based trading model.
    Wraps the PyTorch LSTMNet for sequence-based prediction.
    """

    def __init__(
        self,
        input_size: int = 140,
        hidden_size: int = 64,
        num_layers: int = 2,
        device: str = "cpu",
    ) -> None:
        self.device = torch.device(device)
        self.model = LSTMNet(
            input_size=input_size, hidden_size=hidden_size, num_layers=num_layers
        ).to(self.device)
        self.model.eval()

    def predict(self, features: np.ndarray) -> Signal:
        """
        Predict trading signal from features.
        Expects features to be reshaped to (batch, seq_len, n_features) externally
        or handles basic 2D input by adding a sequence dimension.
        """
        with torch.no_grad():
            # Convert to tensor and add batch/sequence dims if necessary
            # For simplicity, assume features are already correct or flat indicators
            x = torch.from_numpy(features).float().to(self.device)

            if x.dim() == 1:
                # (F,) -> (1, 1, F)
                x = x.unsqueeze(0).unsqueeze(0)
            elif x.dim() == 2:
                # (T, F) -> (1, T, F)
                x = x.unsqueeze(0)

            logits = self.model(x)
            probs = torch.softmax(logits, dim=-1).squeeze(0)

            # Map index to direction
            # Index 0: Hold (0), 1: Buy (1), 2: Sell (-1)
            action_idx = torch.argmax(probs).item()
            confidence = probs[action_idx].item()

            mapping = {0: 0, 1: 1, 2: -1}
            direction = mapping.get(int(action_idx), 0)

            return Signal(direction=direction, confidence=float(confidence))

    def load(self, path: str) -> None:
        """Load model state dict."""
        self.model.load_state_dict(torch.load(path, map_location=self.device))
        self.model.eval()

    def save(self, path: str) -> None:
        """Save model state dict."""
        torch.save(self.model.state_dict(), path)
