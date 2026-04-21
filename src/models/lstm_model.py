"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/lstm_model.py
LSTM sequence model for short-term price prediction using PyTorch.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import numpy as np

from .base_model import BaseModel, Signal

logger = logging.getLogger(__name__)

# Conditional inheritance to allow importing without torch
try:
    import torch
    import torch.nn as nn

    if hasattr(torch, "nn"):
        _Module: Any = nn.Module
    else:
        # Handle cases where torch is a namespace but not fully installed
        _Module = object
        torch = None  # type: ignore
        nn = None  # type: ignore
except ImportError:
    _Module = object
    torch = None  # type: ignore
    nn = None  # type: ignore


class LSTMNetwork(_Module):
    """
    Standard LSTM architecture for sequence processing.
    """

    def __init__(
        self,
        input_size: int,
        hidden_size: int = 64,
        num_layers: int = 2,
        output_size: int = 3,  # 0: Hold, 1: Buy, 2: Sell
        dropout: float = 0.2,
    ) -> None:
        if nn is None:
            raise ImportError("torch.nn is required for LSTMNetwork")
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.lstm = nn.LSTM(
            input_size,
            hidden_size,
            num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x: Any) -> Any:
        # x shape: (batch, seq_len, input_size)
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)

        out, _ = self.lstm(x, (h0, c0))
        # Take the output from the last time step
        out = self.fc(out[:, -1, :])
        return out


class LSTMModel(BaseModel):
    """
    LSTM-based trading model wrapper.
    Implements the BaseModel interface for integration.
    """

    def __init__(
        self,
        input_size: int = 10,
        hidden_size: int = 64,
        num_layers: int = 2,
        device: str = "cpu",
        model_path: Optional[str] = None,
    ) -> None:
        """
        Initialize the LSTM model.

        Args:
            input_size: Number of features per time step.
            hidden_size: Number of hidden units in LSTM.
            num_layers: Number of LSTM layers.
            device: Device to run on ('cpu' or 'cuda').
            model_path: Optional path to load weights.
        """
        if torch is None:
            raise ImportError("torch is required for LSTMModel")

        self.device = torch.device(
            device if torch.cuda.is_available() or device == "cpu" else "cpu"
        )
        self.model = LSTMNetwork(input_size, hidden_size, num_layers).to(self.device)

        if model_path:
            try:
                self.model.load_state_dict(
                    torch.load(model_path, map_location=self.device, weights_only=True)
                )
                logger.info("LSTM weights loaded from %s", model_path)
            except Exception as e:
                logger.error("Failed to load LSTM weights: %s", e)

        self.model.eval()

    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading signal from sequence features.

        Args:
            features: Input features, expected shape (seq_len, n_features)
                      or (batch, seq_len, n_features).

        Returns:
            Signal object.
        """
        # Ensure features are a torch tensor with batch dimension
        if features.ndim == 2:
            # (seq_len, n_features) -> (1, seq_len, n_features)
            x = torch.from_numpy(features).float().unsqueeze(0).to(self.device)
        elif features.ndim == 3:
            x = torch.from_numpy(features).float().to(self.device)
        else:
            raise ValueError(
                f"Unexpected features shape: {features.shape}. Expected 2D or 3D array."
            )

        with torch.no_grad():
            logits = self.model(x)
            probs = torch.softmax(logits, dim=1).cpu().numpy()[0]

        action_idx = int(np.argmax(probs))
        confidence = float(probs[action_idx])

        # Action mapping: 0=Hold, 1=Buy, 2=Sell
        mapping = {0: 0, 1: 1, 2: -1}
        direction = mapping.get(action_idx, 0)

        return Signal(
            direction=direction, confidence=confidence, metadata={"probs": probs.tolist()}
        )
