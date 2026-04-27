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

from src.models.base import BaseModel, Signal

logger = logging.getLogger(__name__)


class LSTMNet(nn.Module):
    """
    Standard LSTM architecture for time-series classification.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 64,
        num_layers: int = 2,
        output_dim: int = 3,
        dropout: float = 0.2
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_dim,
            hidden_dim,
            num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0
        )
        self.fc = nn.Linear(hidden_dim, output_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (batch, seq_len, input_dim)
        out, _ = self.lstm(x)
        # Use only the last hidden state for prediction
        out = self.fc(out[:, -1, :])
        return out


class LSTMModel(BaseModel):
    """
    LSTM-based predictive model wrapper implementing BaseModel interface.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 64,
        num_layers: int = 2,
        device: str = "cpu"
    ) -> None:
        """
        Initialise the LSTM Model.

        Args:
            input_dim: Number of input features per timestep.
            hidden_dim: Number of LSTM hidden units.
            num_layers: Number of LSTM layers.
            device: Device to run the model on.
        """
        self.device = torch.device(device if torch.cuda.is_available() or device == "cpu" else "cpu")
        self.model = LSTMNet(input_dim, hidden_dim, num_layers).to(self.device)
        self.model.eval()

    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading signal from input features.

        Args:
            features: Input features (expected shape: [seq_len, input_dim] or flattened).

        Returns:
            Signal: Predicted direction and confidence.
        """
        # Ensure features are in the correct shape (batch, seq_len, input_dim)
        # This is a simplified stub, actual shape handling might be more complex.
        try:
            # Placeholder for proper feature reshaping
            # If flattened: [window_size * n_features + 2]
            # Here we assume it is already shaped or we can determine seq_len.

            # For the stub, let's assume features is [batch, seq_len, input_dim] or we wrap it.
            if features.ndim == 1:
                # Mock handling for flattened TradingEnv observations
                # In production, this should be explicitly handled.
                x = torch.from_numpy(features).float().to(self.device).unsqueeze(0).unsqueeze(0)
            elif features.ndim == 2:
                x = torch.from_numpy(features).float().to(self.device).unsqueeze(0)
            else:
                x = torch.from_numpy(features).float().to(self.device)

            with torch.no_grad():
                logits = self.model(x)
                probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]

            # Action mapping: 0=Hold, 1=Buy, 2=Sell
            action_idx = int(np.argmax(probs))
            confidence = float(probs[action_idx])

            direction_map = {0: 0, 1: 1, 2: -1}
            direction = direction_map.get(action_idx, 0)

            return Signal(direction=direction, confidence=confidence)

        except Exception as e:
            logger.error(f"LSTM Prediction Error: {e}")
            return Signal(direction=0, confidence=0.0)

    def load(self, path: str) -> None:
        """Load model weights."""
        self.model.load_state_dict(torch.load(path, map_location=self.device))
        self.model.eval()

    def save(self, path: str) -> None:
        """Save model weights."""
        torch.save(self.model.state_dict(), path)
