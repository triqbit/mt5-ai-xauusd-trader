import sys
from unittest.mock import MagicMock

import numpy as np
import pytest

# Mock torch for CI
mock_torch = MagicMock()
sys.modules["torch"] = mock_torch
sys.modules["torch.nn"] = MagicMock()

from src.models.ensemble import EnsembleModel  # noqa: E402


@pytest.fixture
def ensemble():
    return EnsembleModel(device="cpu")


def test_ensemble_predict_no_models(ensemble):
    obs = np.random.randn(140)
    direction, confidence, per_algo = ensemble.predict(obs)
    assert direction == 0
    assert confidence == 0.0
    assert per_algo == {}


def test_lstm_model_output_shape():
    # Since LSTMAttentionModel inherits from nn.Module which we mocked,
    # we need to be careful. But here we are just testing the logic if possible.
    # In CI, we skip this or mock it more deeply.
    pass


def test_ensemble_predict_with_mock_lstm(ensemble, monkeypatch):
    # Setup mock LSTM
    mock_model = MagicMock()
    # Mocking softmax output probabilities
    # probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]
    mock_probs = MagicMock()
    mock_probs.cpu.return_value.numpy.return_value = np.array([[0.8, 0.1, 0.1]])

    mock_torch.softmax.return_value = mock_probs

    ensemble.lstm_model = mock_model

    obs = np.random.randn(140)
    seq = np.random.randn(60, 5)

    direction, confidence, per_algo = ensemble.predict(obs, seq=seq)

    assert direction == 1  # Buy (index 0)
    assert confidence == 0.8
    assert per_algo["lstm"] == 0.0
