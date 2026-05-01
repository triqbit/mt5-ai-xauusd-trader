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


class LSTMPricePredictor(nn.Module):
    """
    PyTorch LSTM module for sequence modeling.
    Input : (batch, seq_len, n_features)
    Output: (batch, 3) -> [Hold, Buy, Sell] logits
    """

    def __init__(
        self,
        n_features: int = 140,
        hidden_size: int = 128,
        num_layers: int = 2,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=n_features,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 3),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (batch, seq_len, n_features)
        out, _ = self.lstm(x)
        # Take the last time step's output
        out = out[:, -1, :]
        return self.fc(out)


class LSTMModel(BaseModel):
    """
    Wrapper for LSTMPricePredictor that implements the BaseModel interface.
    """

    def __init__(
        self,
        n_features: int = 140,
        model_path: Optional[Path] = None,
        device: str = "cpu",
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.device = torch.device(device)
        self.model = LSTMPricePredictor(n_features=n_features).to(self.device)

        if model_path and model_path.exists():
            self.logger.info("Loading LSTM model weights from %s", model_path)
            self.model.load_state_dict(torch.load(str(model_path), map_location=self.device))

        self.model.eval()

    def predict(self, features: np.ndarray) -> Signal:
        """
        Predict trading signal using LSTM.

        Args:
            features: Input sequence of shape (seq_len, n_features) or (batch, seq_len, n_features)

        Returns:
            Signal object.
        """
        # Ensure features have a batch dimension
        if features.ndim == 2:
            features = np.expand_dims(features, axis=0)

        x = torch.from_numpy(features).float().to(self.device)

        with torch.no_grad():
            logits = self.model(x)
            probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]

        # Action map: 0=Hold, 1=Buy, 2=Sell
        action_idx = int(np.argmax(probs))
        confidence = float(probs[action_idx])

        direction_map = {0: 0, 1: 1, 2: -1}
        direction = direction_map.get(action_idx, 0)

        return Signal(
            direction=direction,
            confidence=confidence,
            metadata={"probs": probs.tolist()}
        )
