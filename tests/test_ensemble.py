import pytest
import numpy as np
import torch
from src.models.ensemble import EnsembleModel, LSTMAttentionModel

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
    model = LSTMAttentionModel(n_features=5)
    seq = torch.randn(1, 10, 5)
    output = model(seq)
    assert output.shape == (1, 3)

def test_ensemble_predict_with_mock_lstm(ensemble, monkeypatch):
    # Setup mock LSTM
    class MockLSTM(torch.nn.Module):
        def __init__(self):
            super().__init__()
        def forward(self, x):
            # Return high probability for Buy (index 0)
            return torch.tensor([[10.0, -10.0, -10.0]])

    mock_model = MockLSTM()
    ensemble.lstm_model = mock_model

    obs = np.random.randn(140)
    seq = np.random.randn(60, 5) # Matches main.py window_size and dummy features

    direction, confidence, per_algo = ensemble.predict(obs, seq=seq)

    assert direction == 1 # Buy
    assert confidence > 0.9
    assert per_algo["lstm"] == 0.0
