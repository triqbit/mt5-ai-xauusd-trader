"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/lstm_model.py
LSTM sequence model using PyTorch for short-term price prediction.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn

from src.models.base import BaseModel, Signal

logger = logging.getLogger(__name__)


class LSTMNetwork(nn.Module):
    """
    Core PyTorch LSTM architecture for time-series classification.
    """

    def __init__(
        self,
        input_size: int = 140,
        hidden_size: int = 64,
        num_layers: int = 2,
        output_size: int = 3,
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
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (batch, seq_len, input_size)
        out, _ = self.lstm(x)
        # Use only the last time step output
        out = self.fc(out[:, -1, :])
        return out


class LSTMModel(BaseModel):
    """
    Wrapper for LSTMNetwork providing the BaseModel interface.
    Handles data preprocessing and PyTorch lifecycle.
    """

    def __init__(
        self,
        input_size: int = 140,
        hidden_size: int = 64,
        num_layers: int = 2,
        device: str = "cpu",
        model_path: Optional[Path | str] = None,
    ) -> None:
        self.device = torch.device(device)
        self.network = LSTMNetwork(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
        ).to(self.device)

        if model_path and Path(model_path).exists():
            logger.info("Loading LSTM weights from %s", model_path)
            self.network.load_state_dict(
                torch.load(str(model_path), map_location=self.device)
            )

        self.network.eval()

    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading signal from input features.

        Args:
            features: np.ndarray of shape (seq_len, input_size) or (input_size,)

        Returns:
            Signal: Direction (1, -1, 0) and confidence score.
        """
        # Ensure features are in (batch, seq_len, input_size) format
        if features.ndim == 1:
            # Assume it's a single feature vector, we might need a dummy sequence dimension
            # Or this model expects a sequence.
            x = torch.from_numpy(features).float().unsqueeze(0).unsqueeze(0)
        elif features.ndim == 2:
            x = torch.from_numpy(features).float().unsqueeze(0)
        else:
            x = torch.from_numpy(features).float()

        x = x.to(self.device)

        with torch.no_grad():
            logits = self.network(x)
            probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]

        # Action mapping: 0=Hold, 1=Buy, 2=Sell
        action_idx = int(np.argmax(probs))
        confidence = float(probs[action_idx])

        direction_map = {0: 0, 1: 1, 2: -1}
        direction = direction_map[action_idx]

        return Signal(direction=direction, confidence=confidence)

    def save(self, path: Path | str) -> None:
        """Save model weights."""
        torch.save(self.network.state_dict(), str(path))
        logger.info("LSTM model saved to %s", path)
