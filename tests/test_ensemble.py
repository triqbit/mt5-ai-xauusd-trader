"""Tests for EnsembleModel."""
import pytest
import torch
import numpy as np
from unittest.mock import MagicMock
from src.models.ensemble import EnsembleModel, LSTMAttentionModel

def test_lstm_model_forward():
    model = LSTMAttentionModel(n_features=10, hidden_size=32, num_layers=1, n_heads=2)
    x = torch.randn(1, 20, 10) # (B, T, F)
    out = model(x)
    assert out.shape == (1, 3)

def test_ensemble_predict_no_models():
    ensemble = EnsembleModel()
    obs = np.random.randn(200)
    direction, confidence, per_algo = ensemble.predict(obs)
    assert direction == 0
    assert confidence == 0.0
    assert per_algo == {}

def test_ensemble_predict_with_lstm():
    ensemble = EnsembleModel()
    # Mock LSTM
    mock_lstm = MagicMock(spec=LSTMAttentionModel)
    # Output: High probability for BUY (index 0)
    mock_lstm.return_value = torch.tensor([[5.0, -5.0, -5.0]])
    ensemble.lstm_model = mock_lstm

    obs = np.random.randn(200)
    seq = torch.randn(20, 140)
    direction, confidence, per_algo = ensemble.predict(obs, seq=seq)

    assert direction == 1 # BUY
    assert confidence > 0.9
    assert per_algo["lstm"] == 0 # Index 0

def test_ensemble_consensus_fail():
    ensemble = EnsembleModel()

    # Mock PPO to vote BUY
    ensemble._ppo_model = MagicMock()
    ensemble._ppo_model.predict.return_value = (0, None)

    # Mock LSTM to vote SELL
    ensemble.lstm_model = MagicMock()
    ensemble.lstm_model.return_value = torch.tensor([[-5.0, 5.0, -5.0]])

    obs = np.random.randn(200)
    seq = torch.randn(20, 140)

    # Even weights, one BUY, one SELL -> consensus should fail if ratio < 0.6
    # 2 models, 1 agrees -> 0.5 agreement ratio.
    direction, confidence, per_algo = ensemble.predict(obs, seq=seq)

    assert direction == 0 # Consensus failure defaults to HOLD
