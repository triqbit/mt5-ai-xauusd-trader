"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/lstm_model.py
LSTM sequence model for short-term price prediction using PyTorch.
"""

import logging
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from src.models.base import BaseModel, Signal

logger = logging.getLogger(__name__)


class LSTMNetwork(nn.Module):
    """
    Standard LSTM network for sequence classification.
    Input: (Batch, Sequence, Features)
    Output: (Batch, 3) -> [Hold, Buy, Sell] logits
    """

    def __init__(
        self,
        n_features: int,
        hidden_size: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2
    ):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=n_features,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0
        )
        self.fc = nn.Linear(hidden_size, 3)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (Batch, Seq, Features)
        out, _ = self.lstm(x)
        # Take the last time step's output
        out = self.fc(out[:, -1, :])
        return out


class LSTMModel(BaseModel):
    """
    LSTM sequence model wrapper.
    Inherits from BaseModel.
    """

    def __init__(
        self,
        n_features: int = 140,
        hidden_size: int = 64,
        num_layers: int = 2,
        device: str = "cpu"
    ):
        """
        Initialize the LSTM model.

        Args:
            n_features: Number of input features.
            hidden_size: Number of hidden units in LSTM.
            num_layers: Number of LSTM layers.
            device: 'cpu' or 'cuda'.
        """
        self.device = torch.device(device if torch.cuda.is_available() or device == "cpu" else "cpu")
        self.network = LSTMNetwork(
            n_features=n_features,
            hidden_size=hidden_size,
            num_layers=num_layers
        ).to(self.device)
        self.network.eval()

    def load(self, path: Path) -> None:
        """Load model weights."""
        if path.exists():
            self.network.load_state_dict(torch.load(str(path), map_location=self.device))
            self.network.eval()
            logger.info("LSTM weights loaded from %s", path)
        else:
            logger.warning("LSTM weights not found at %s", path)

    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading signal from sequence features.

        Args:
            features: Input array of shape (seq_len, n_features) or (batch, seq_len, n_features).

        Returns:
            Signal: direction and confidence.
        """
        # Convert to torch tensor and add batch dim if necessary
        if features.ndim == 2:
            x = torch.from_numpy(features).float().unsqueeze(0).to(self.device)
        elif features.ndim == 3:
            x = torch.from_numpy(features).float().to(self.device)
        else:
            logger.error("Invalid features shape for LSTM: %s", features.shape)
            return Signal(direction=0, confidence=0.0)

        with torch.no_grad():
            logits = self.network(x)
            probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]

        # Action: 0=Hold, 1=Buy, 2=Sell
        action_idx = int(np.argmax(probs))
        confidence = float(probs[action_idx])

        direction_map = {0: 0, 1: 1, 2: -1}
        direction = direction_map.get(action_idx, 0)

        return Signal(direction=direction, confidence=confidence)
