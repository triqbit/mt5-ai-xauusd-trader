"""Tests for EnsembleModel."""
import pytest
import numpy as np
import torch
from unittest.mock import MagicMock
from src.models.ensemble import EnsembleModel

def test_ensemble_predict_consensus():
    # Setup ensemble with a mock PPO model
    ensemble = EnsembleModel(device="cpu", consensus_threshold=0.6)

    # Mocking votes
    mock_ppo = MagicMock()
    # PPO returns action 0 (Buy)
    mock_ppo.predict.return_value = (0, None)
    ensemble._ppo_model = mock_ppo

    obs = np.zeros(140)
    direction, confidence, per_algo = ensemble.predict(obs)

    # With only one model, confidence will be 1.0 for Buy
    assert direction == 1
    assert confidence == 1.0
    assert per_algo["ppo"] == 0

def test_ensemble_consensus_not_reached():
    ensemble = EnsembleModel(device="cpu", consensus_threshold=0.8)

    # We need to simulate two models disagreeing to lower confidence
    # Let's mock _ppo_model and lstm_model
    ensemble._ppo_model = MagicMock()
    ensemble._ppo_model.predict.return_value = (0, None) # Buy

    ensemble.lstm_model = MagicMock()
    # LSTM returns Sell (action 1) with high probability
    ensemble.lstm_model.side_effect = lambda x: torch.tensor([[0.1, 0.8, 0.1]])

    ensemble.weights = {"ppo": 0.5, "lstm": 0.5}

    obs = np.zeros(140)
    seq = torch.zeros((10, 140))

    direction, confidence, per_algo = ensemble.predict(obs, seq=seq)

    # PPO: [1, 0, 0], LSTM: [0.1, 0.8, 0.1]
    # Blended: [0.55, 0.4, 0.05]
    # Max is 0.55 (Buy)
    # Threshold is 0.8 -> should return HOLD
    assert direction == 0
