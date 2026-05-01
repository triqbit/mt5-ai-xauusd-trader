"""
Unit tests for TimeSeriesTransformer.
"""
import pytest
import torch
from src.models.transformer_model import TimeSeriesTransformer

def test_transformer_forward():
    input_dim = 10
    model = TimeSeriesTransformer(input_dim=input_dim, model_dim=32, num_heads=4, num_layers=2)
    x = torch.randn(2, 20, input_dim) # [batch, seq, input_dim]
    out = model(x)
    assert out.shape == (2, 3)
    assert torch.allclose(out.sum(dim=-1), torch.tensor([1.0, 1.0]))
