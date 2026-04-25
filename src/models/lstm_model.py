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


class LSTMPricePredictor(nn.Module):
    """
    Core LSTM network architecture.
    """

    def __init__(
        self,
        input_dim: int = 140,
        hidden_dim: int = 128,
        num_layers: int = 2,
        output_dim: int = 3,
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_dim, hidden_dim, num_layers, batch_first=True, dropout=0.2
        )
        self.fc = nn.Linear(hidden_dim, output_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (batch, seq_len, input_dim)
        out, _ = self.lstm(x)
        # take the last time step
        out = self.fc(out[:, -1, :])
        return out


class LSTMModel(BaseModel):
    """
    Wrapper for LSTMPricePredictor compatible with the BaseModel interface.
    """

    def __init__(
        self,
        model_path: Optional[Path] = None,
        input_dim: int = 140,
        device: str = "cpu",
    ) -> None:
        self.device = torch.device(device)
        self.model = LSTMPricePredictor(input_dim=input_dim).to(self.device)

        if model_path and Path(model_path).exists():
            logger.info("Loading LSTM model from %s", model_path)
            self.model.load_state_dict(
                torch.load(str(model_path), map_location=self.device)
            )

        self.model.eval()

    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading signal from input features.
        Expects features to be (seq_len, n_features) or (batch, seq_len, n_features)
        """
        # Convert to torch tensor and add batch dim if necessary
        if features.ndim == 2:
            x = torch.from_numpy(features).float().unsqueeze(0).to(self.device)
        else:
            x = torch.from_numpy(features).float().to(self.device)

        with torch.no_grad():
            logits = self.model(x)
            probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]

        # Mapping: 0=Buy, 1=Sell, 2=Hold
        # We'll use a common mapping across models for the Signal object
        action_idx = int(np.argmax(probs))
        confidence = float(probs[action_idx])

        mapping = {0: 1, 1: -1, 2: 0}
        direction = mapping.get(action_idx, 0)

        return Signal(direction=direction, confidence=confidence)
