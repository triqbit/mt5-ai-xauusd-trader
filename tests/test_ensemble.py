"""Tests for EnsembleModel."""
import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from src.models.ensemble import EnsembleModel

def test_ensemble_predict_no_models():
    ensemble = EnsembleModel()
    obs = np.random.randn(200)
    direction, confidence, per_algo = ensemble.predict(obs)
    assert direction == 0
    assert confidence == 0.0
    assert per_algo == {}

@patch('src.models.ensemble.get_lstm_model_class')
def test_ensemble_predict_with_lstm(mock_get_class):
    torch = pytest.importorskip("torch")

    ensemble = EnsembleModel()
    # Mock LSTM
    mock_lstm = MagicMock()
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
    torch = pytest.importorskip("torch")

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
    direction, confidence, per_algo = ensemble.predict(obs, seq=seq)

    assert direction == 0 # Consensus failure defaults to HOLD
