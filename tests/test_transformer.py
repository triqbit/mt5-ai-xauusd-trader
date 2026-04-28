"""Tests for transformer model."""
from __future__ import annotations

import torch

from src.models.transformer_model import PositionalEncoding, TimeSeriesTransformer


def test_transformer_forward() -> None:
    """Test TimeSeriesTransformer forward pass."""
    input_dim = 140
    seq_len = 60
    batch_size = 8
    model = TimeSeriesTransformer(input_dim=input_dim, model_dim=64, num_heads=4, num_layers=2)
    x = torch.randn(batch_size, seq_len, input_dim)
    out = model(x)
    assert out.shape == (batch_size, 3)


def test_positional_encoding() -> None:
    """Test PositionalEncoding."""
    d_model = 64
    seq_len = 60
    batch_size = 8
    pe = PositionalEncoding(d_model=d_model, dropout=0.0)
    x = torch.randn(batch_size, seq_len, d_model)
    out = pe(x)
    assert out.shape == (batch_size, seq_len, d_model)
    # Check that it's not the same as input
    assert not torch.equal(x, out)
