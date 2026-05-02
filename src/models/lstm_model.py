"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/lstm_model.py
LSTM sequence model using PyTorch for short-term price prediction.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

import numpy as np

try:
    import torch
    import torch.nn as nn
except ImportError:
    torch = None  # type: ignore
    nn = None  # type: ignore

# Prevent AttributeError when torch is None during type hint evaluation
if torch is None:

    class MockTensor:
        pass

    class MockTorch:
        Tensor = MockTensor

    torch = MockTorch()  # type: ignore

if TYPE_CHECKING:
    import torch

from src.core.constants import SignalDirection
from src.models.base_model import BaseModel, Signal


class LSTMPricePredictor(nn.Module if nn else object):
    """Simple LSTM for price direction prediction."""

    def __init__(self, input_dim: int, hidden_dim: int = 64, num_layers: int = 2):
        if not nn:
            raise ImportError("PyTorch is required for LSTMPricePredictor")
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_dim, 3)  # [hold, buy, sell]

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if not hasattr(torch, "from_numpy"):  # Real torch check
            raise ImportError("PyTorch is required for forward pass")
        _, (hn, _) = self.lstm(x)
        out = self.fc(hn[-1])
        return out


class LSTMModel(BaseModel):
    """
    Wrapper for LSTMPricePredictor implementing BaseModel interface.
    """

    def __init__(
        self,
        input_dim: int = 140,
        model_path: Optional[Union[str, Path]] = None,
        device: str = "cpu",
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.device = (
            torch.device(device)
            if torch and device != "auto"
            else torch.device("cpu")
            if torch
            else None
        )
        self.model = None

        if torch:
            self.model = LSTMPricePredictor(input_dim).to(self.device)
            if model_path and Path(model_path).exists():
                self.model.load_state_dict(torch.load(model_path, map_location=self.device))
                self.model.eval()

    def predict(self, features: np.ndarray) -> Signal:
        """
        Predict price direction using LSTM.
        """
        if self.model is None or not torch:
            return Signal(
                direction=SignalDirection.HOLD,
                confidence=0.0,
                metadata={"error": "Model not loaded"},
            )

        # features expected as (seq_len, n_features) or (batch, seq_len, n_features)
        x = torch.from_numpy(features).float().to(self.device)
        if x.dim() == 2:
            x = x.unsqueeze(0)

        with torch.no_grad():
            logits = self.model(x)
            probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]

        action_idx = np.argmax(probs)
        confidence = float(probs[action_idx])

        # 0: hold, 1: buy, 2: sell
        direction_map = {0: SignalDirection.HOLD, 1: SignalDirection.BUY, 2: SignalDirection.SELL}

        return Signal(
            direction=direction_map.get(action_idx, SignalDirection.HOLD),
            confidence=confidence,
            metadata={"probs": probs.tolist()},
        )
