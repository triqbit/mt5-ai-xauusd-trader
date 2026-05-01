"""
Unit tests for EnsembleModel.
"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import numpy as np
import torch
from src.models.ensemble import EnsembleModel, LSTMAttentionModel

@pytest.fixture
def ensemble():
    return EnsembleModel(device="cpu")

def test_ensemble_init(ensemble):
    assert ensemble.ALGORITHMS == ["ppo", "dreamer", "lstm"]
    assert ensemble.weights["ppo"] == pytest.approx(1/3)

@patch("stable_baselines3.PPO")
def test_load_ppo(mock_ppo, ensemble):
    path = Path("test_ppo.zip")
    ensemble.load_ppo(path)
    mock_ppo.load.assert_called_once()
    assert ensemble._ppo_model is not None

def test_load_lstm(ensemble):
    # Create a dummy state dict
    model = LSTMAttentionModel(n_features=10)
    state_dict = model.state_dict()
    path = Path("test_lstm.pt")
    torch.save(state_dict, path)

    ensemble.load_lstm(path, n_features=10)
    assert ensemble.lstm_model is not None
    path.unlink()

def test_predict_hold_no_models(ensemble):
    obs = np.zeros(140)
    dir, conf, per_algo = ensemble.predict(obs)
    assert dir == 0
    assert conf == 0.0
    assert per_algo == {}

def test_record_return_and_rebalance(ensemble):
    for _ in range(60):
        ensemble.record_return("ppo", 0.01)
        ensemble.record_return("lstm", 0.02)
        ensemble.record_return("dreamer", 0.005)

    assert ensemble.weights["lstm"] > ensemble.weights["dreamer"]
    assert sum(ensemble.weights.values()) == pytest.approx(1.0)

def test_lstm_attention_model_forward():
    model = LSTMAttentionModel(n_features=10, hidden_size=32, num_layers=1, n_heads=4)
    x = torch.randn(1, 5, 10) # (batch, seq, features)
    out = model(x)
    assert out.shape == (1, 3)
