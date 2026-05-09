"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/transformer_model.py
Transformer-based architecture for time-series forecasting and signal generation.
"""

import math
from typing import Any

import numpy as np

try:
    import torch
    import torch.nn as nn
except ImportError:
    torch = None
    nn = None

from src.core.constants import ModelAction, SignalDirection
from src.models.base_model import BaseModel, Signal


class TimeSeriesTransformer(BaseModel):
    """
    Advanced Transformer model for price action forecasting.
    Input: [batch_size, seq_len, features]
    Output: [batch_size, 3] (Hold, Buy, Sell) - Aligned with ModelAction.
    """

    def __init__(
        self,
        input_dim: int,
        model_dim: int = 128,
        num_heads: int = 8,
        num_layers: int = 4,
        dropout: float = 0.1,
    ):
        super().__init__()
        if not nn:
            self._module = None
            return

        class TransformerModule(nn.Module):
            def __init__(self, input_dim, model_dim, num_heads, num_layers, dropout):
                super().__init__()
                self.model_dim = model_dim
                self.pos_encoder = PositionalEncoding(model_dim, dropout)
                encoder_layers = nn.TransformerEncoderLayer(
                    d_model=model_dim,
                    nhead=num_heads,
                    dim_feedforward=model_dim * 4,
                    dropout=dropout,
                    batch_first=True,
                )
                self.transformer_encoder = nn.TransformerEncoder(encoder_layers, num_layers)
                self.input_projection = nn.Linear(input_dim, model_dim)
                self.decoder = nn.Linear(model_dim, 3)

            def forward(self, src):
                src = self.input_projection(src) * math.sqrt(self.model_dim)
                src = self.pos_encoder(src)
                output = self.transformer_encoder(src)
                output = self.decoder(output[:, -1, :])
                return torch.softmax(output, dim=-1)

        self._module = TransformerModule(input_dim, model_dim, num_heads, num_layers, dropout)

    def forward(self, src: Any) -> Any:
        if self._module:
            return self._module(src)
        raise RuntimeError("Torch not available")

    def eval(self) -> None:
        if self._module:
            self._module.eval()

    def load_state_dict(self, state_dict: Any) -> None:
        if self._module:
            self._module.load_state_dict(state_dict)

    def predict(self, features: np.ndarray, **kwargs: Any) -> Signal:
        """
        Generate a trading signal from input features using the Transformer model.

        Args:
            features: Current observation (ignored if seq provided).
            **kwargs: Must contain 'seq' (np.ndarray) of shape (seq_len, input_dim).

        Returns:
            Signal: Consolidated signal.
        """
        if not torch or not nn or not self._module:
            return Signal(
                direction=SignalDirection.HOLD,
                confidence=0.0,
                metadata={"error": "PyTorch missing"},
            )

        seq = kwargs.get("seq")
        if seq is None:
            # Fallback to features if seq not provided (might fail if shape is wrong)
            seq = features

        try:
            # Handle sequence shape
            if isinstance(seq, np.ndarray):
                x = torch.from_numpy(seq).float()
            else:
                x = seq

            if x.dim() == 2:
                x = x.unsqueeze(0)  # Add batch dim

            self.eval()
            with torch.no_grad():
                probs = self.forward(x)
                probs_np = probs.cpu().numpy()[0]

            action_idx = int(np.argmax(probs_np))
            confidence = float(probs_np[action_idx])

            # Explicitly map ModelAction to SignalDirection via helper
            direction = ModelAction(action_idx).to_direction()

            return Signal(
                direction=direction,
                confidence=confidence,
                metadata={"probabilities": probs_np.tolist()},
            )
        except Exception as e:
            return Signal(
                direction=SignalDirection.HOLD,
                confidence=0.0,
                metadata={"error": str(e)},
            )


class PositionalEncoding(nn.Module if nn else object):
    """Injects positional information into the sequence."""

    def __init__(self, d_model: int, dropout: float = 0.1, max_len: int = 5000):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.register_buffer("pe", pe)

    def forward(self, x: Any) -> Any:
        # x shape: [batch_size, seq_len, d_model]
        x = x + self.pe[:, : x.size(1), :]
        return self.dropout(x)
