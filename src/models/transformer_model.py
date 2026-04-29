"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/transformer_model.py
Transformer-based architecture for time-series forecasting and signal generation.
"""

import math

try:
    import torch
    import torch.nn as nn

    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    nn = None
    TORCH_AVAILABLE = False


class TimeSeriesTransformer(nn.Module if TORCH_AVAILABLE else object):
    """
    Advanced Transformer model for price action forecasting.
    Input: [batch_size, seq_len, features]
    Output: [batch_size, 3] (Buy, Sell, Hold)
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
        self.model_dim = model_dim
        self.pos_encoder = PositionalEncoding(model_dim, dropout)

        # Transformer Encoder
        encoder_layers = nn.TransformerEncoderLayer(
            d_model=model_dim,
            nhead=num_heads,
            dim_feedforward=model_dim * 4,
            dropout=dropout,
            batch_first=True,
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layers, num_layers)

        # Input and Output Projections
        self.input_projection = nn.Linear(input_dim, model_dim)
        self.decoder = nn.Linear(model_dim, 3)  # Output: [Long, Short, Neutral] probabilities

    def forward(self, src: torch.Tensor) -> torch.Tensor:
        # src shape: [batch_size, seq_len, input_dim]
        src = self.input_projection(src) * math.sqrt(self.model_dim)
        src = self.pos_encoder(src)
        output = self.transformer_encoder(src)

        # Use only the last time step for classification
        output = self.decoder(output[:, -1, :])
        return torch.softmax(output, dim=-1)


class PositionalEncoding(nn.Module if TORCH_AVAILABLE else object):
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

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: [batch_size, seq_len, d_model]
        x = x + self.pe[:, : x.size(1), :]
        return self.dropout(x)
