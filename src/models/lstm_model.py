"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/lstm_model.py
LSTM sequence model using PyTorch for short-term price prediction.
"""

from __future__ import annotations

import logging
from typing import Any

import torch
import torch.nn as nn

from src.models.base import BaseModel, Signal

logger = logging.getLogger(__name__)


class LSTMPredictor(nn.Module):
    """
    Core PyTorch LSTM network.
    """

    def __init__(
        self, input_size: int = 10, hidden_size: int = 64, num_layers: int = 2, output_size: int = 3
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len, input_size)
        out, _ = self.lstm(x)
        # Take the last time step
        out = out[:, -1, :]
        out = self.fc(out)
        return out


class LSTMModel(BaseModel):
    """
    LSTM-based price prediction model wrapper.
    """

    def __init__(
        self, input_size: int = 10, hidden_size: int = 64, num_layers: int = 2, device: str = "cpu"
    ) -> None:
        self.device = torch.device(device)
        self.model = LSTMPredictor(input_size, hidden_size, num_layers).to(self.device)
        self.model.eval()

    def predict(self, features: Any) -> Signal:
        """
        Predict short-term price movement direction.

        Args:
            features: Input sequence (numpy array or torch tensor).

        Returns:
            A Signal object.
        """
        if not isinstance(features, torch.Tensor):
            features = torch.tensor(features, dtype=torch.float32)

        # Ensure correct shape (batch, seq_len, input_size)
        if features.ndim == 2:
            features = features.unsqueeze(0)

        features = features.to(self.device)

        with torch.no_grad():
            logits = self.model(features)
            probs = torch.softmax(logits, dim=1)
            action_idx = torch.argmax(probs, dim=1).item()
            confidence = probs[0, action_idx].item()

        # Mapping: 0=Hold, 1=Buy, 2=Sell
        direction_map = {0: 0, 1: 1, 2: -1}
        direction = direction_map.get(action_idx, 0)

        return Signal(
            direction=direction,
            confidence=float(confidence),
            metadata={"logits": logits.cpu().numpy().tolist()},
        )

    def load_state_dict(self, path: str) -> None:
        """Load model weights from a file."""
        self.model.load_state_dict(torch.load(path, map_location=self.device))
        self.model.eval()
