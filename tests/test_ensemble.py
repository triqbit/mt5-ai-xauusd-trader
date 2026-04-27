"""Tests for src.models.ensemble module."""
import pytest
import numpy as np
import torch
from unittest.mock import MagicMock, patch
from src.models.ensemble import EnsembleModel, LSTMAttentionModel

def test_lstm_attention_model_forward():
    n_features = 10
    model = LSTMAttentionModel(n_features=n_features, hidden_size=16, num_layers=1, n_heads=2)
    x = torch.randn(2, 5, n_features) # (batch, seq_len, features)
    out = model(x)
    assert out.shape == (2, 3)

def test_ensemble_model_initialization():
    ensemble = EnsembleModel()
    assert ensemble.consensus_threshold == 0.60
    assert ensemble.veto_threshold == 0.40
    assert "ppo" in ensemble.weights
    assert "lstm" in ensemble.weights

def test_ensemble_predict_no_models():
    ensemble = EnsembleModel()
    direction, confidence, per_algo = ensemble.predict(np.zeros(140))
    assert direction == 0
    assert confidence == 0.0
    assert per_algo == {}

@patch("src.models.ensemble.torch.load")
def test_ensemble_predict_with_veto(mock_load):
    ensemble = EnsembleModel(veto_threshold=0.5)

    # Mock LSTM model
    mock_lstm = MagicMock(spec=LSTMAttentionModel)
    # Use high logits to ensure deterministic softmax output
    # Logits [-1, -1, -1] -> probs [0.33, 0.33, 0.33] -> max 0.33 < 0.5 (Veto)
    mock_lstm.return_value = torch.tensor([[-1.0, -1.0, -1.0]])
    ensemble.lstm_model = mock_lstm

    obs = np.zeros(10)
    seq = torch.zeros(5, 10)

    direction, confidence, _per_algo = ensemble.predict(obs, seq=seq)

    assert direction == 0 # Vetoed
    assert confidence < 0.5

def test_ensemble_predict_consensus_success():
    ensemble = EnsembleModel(consensus_threshold=0.6)

    # Mock PPO and LSTM to agree
    ensemble._ppo_model = MagicMock()
    ensemble._ppo_model.predict.return_value = (0, None) # Index 0 -> direction 1 (Buy)

    ensemble.lstm_model = MagicMock()
    # Logits that result in high prob for index 0
    ensemble.lstm_model.return_value = torch.tensor([[10.0, -10.0, -10.0]])

    obs = np.zeros(10)
    seq = torch.zeros(5, 10)

    direction, confidence, per_algo = ensemble.predict(obs, seq=seq)

    assert direction == 1 # Buy
    assert confidence >= 0.6
    assert per_algo["ppo"] == 0
    assert per_algo["lstm"] == 0

def test_ensemble_predict_no_consensus():
    ensemble = EnsembleModel(consensus_threshold=0.8)

    ensemble._ppo_model = MagicMock()
    ensemble._ppo_model.predict.return_value = (0, None) # Buy

    ensemble.lstm_model = MagicMock()
    ensemble.lstm_model.return_value = torch.tensor([[-10.0, 10.0, -10.0]]) # Sell

    obs = np.zeros(10)
    seq = torch.zeros(5, 10)

    direction, confidence, _per_algo = ensemble.predict(obs, seq=seq)

    assert direction == 0 # No consensus
    assert confidence < 0.8
    assert pytest.approx(confidence, 0.01) == 0.5
