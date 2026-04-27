import pytest
import numpy as np
import torch
from src.models.ensemble import EnsembleModel, LSTMAttentionModel

def test_lstm_model_forward():
    model = LSTMAttentionModel(n_features=10, hidden_size=16, n_heads=2)
    x = torch.randn(4, 5, 10) # (batch, seq, features)
    out = model(x)
    assert out.shape == (4, 3)

def test_ensemble_no_models():
    ensemble = EnsembleModel(device="cpu")
    direction, confidence, per_algo = ensemble.predict(np.zeros(140))
    assert direction == 0
    assert confidence == 0.0
    assert per_algo == {}

def test_ensemble_weight_adaptation():
    ensemble = EnsembleModel(device="cpu")
    # Record some good performance for 'ppo'
    for _ in range(60):
        ensemble.record_return("ppo", 0.02)
        ensemble.record_return("lstm", -0.01)

    # Weights should favor PPO now
    assert ensemble.weights["ppo"] > ensemble.weights["lstm"]
    assert ensemble.weights["ppo"] > 0.33
