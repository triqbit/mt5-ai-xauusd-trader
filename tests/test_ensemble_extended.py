"""Extended tests for src.models.ensemble module."""
import pytest
import numpy as np
import torch
from unittest.mock import MagicMock
from src.models.ensemble import EnsembleModel

def test_ensemble_predict_weighted_consensus():
    ensemble = EnsembleModel(device="cpu")

    # Mock PPO
    mock_ppo = MagicMock()
    # PPO returns 0 (Buy)
    mock_ppo.predict.return_value = (0, None)
    ensemble._ppo_model = mock_ppo

    # Mock LSTM
    ensemble.lstm_model = MagicMock()
    # LSTM returns 1 (Sell) with high confidence
    # Forward pass returns logits [buy, sell, hold]
    # Let's say it returns [0.1, 0.8, 0.1] -> Sell
    ensemble.lstm_model.return_value = torch.tensor([[0.1, 0.8, 0.1]])

    # Equal weights (1/3 each)
    ensemble.weights = {"ppo": 0.5, "lstm": 0.5, "dreamer": 0.0}

    obs = np.random.rand(10)
    seq = torch.rand(1, 10, 140)

    direction, confidence, per_algo = ensemble.predict(obs, seq)

    # PPO: Buy (index 0) -> probs [1.0, 0.0, 0.0]
    # LSTM: Logits [0.1, 0.8, 0.1] -> Softmax probs ~[0.25, 0.50, 0.25]
    # Blended Buy (0.5*1.0 + 0.5*0.25) = 0.625
    # Blended Sell (0.5*0.0 + 0.5*0.50) = 0.25
    # Winner: Buy (direction +1)
    assert direction == 1
    assert confidence == pytest.approx(0.625, abs=0.01)
    assert per_algo["ppo"] == 0.0 # Buy index
    assert per_algo["lstm"] == 1.0 # Sell index

def test_ensemble_weight_rebalancing():
    ensemble = EnsembleModel()
    # Record some good returns for PPO and bad for LSTM
    for _ in range(60):
        ensemble.record_return("ppo", 0.05)
        ensemble.record_return("lstm", -0.05)
        ensemble.record_return("dreamer", 0.01)

    # After 50, it should have rebalanced
    assert ensemble.weights["ppo"] > ensemble.weights["lstm"]
    assert ensemble.weights["ppo"] > ensemble.weights["dreamer"]
    assert pytest.approx(sum(ensemble.weights.values())) == 1.0
