"""Tests for src.models.ensemble module."""
import pytest
import numpy as np
import torch
from src.models.ensemble import EnsembleModel, LSTMAttentionModel

def test_lstm_attention_forward():
    """Test the LSTM+Attention model forward pass."""
    batch_size = 2
    seq_len = 10
    n_features = 140
    model = LSTMAttentionModel(n_features=n_features)
    x = torch.randn(batch_size, seq_len, n_features)
    out = model(x)
    assert out.shape == (batch_size, 3)

def test_ensemble_predict_no_models():
    """Test ensemble prediction when no sub-models are loaded."""
    ensemble = EnsembleModel()
    obs = np.random.rand(140)
    direction, confidence, per_algo = ensemble.predict(obs)
    assert direction == 0
    assert confidence == 0.0
    assert per_algo == {}

def test_ensemble_weight_rebalance():
    """Test ensemble weight rebalancing based on performance."""
    ensemble = EnsembleModel()
    # Initially equal weights
    assert pytest.approx(ensemble.weights["ppo"], 0.01) == 0.333

    # Record some performance (ppo performing well, others poorly)
    for _ in range(50):
        ensemble.record_return("ppo", 0.02)
        ensemble.record_return("lstm", -0.01)
        ensemble.record_return("dreamer", 0.0)

    # Weights should have shifted towards PPO
    assert ensemble.weights["ppo"] > 0.333
    assert ensemble.weights["lstm"] < 0.333
    assert pytest.approx(sum(ensemble.weights.values())) == 1.0
