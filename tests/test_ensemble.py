"""Tests for src.models.ensemble module."""
import pytest
import numpy as np
import torch
from src.models.ensemble import EnsembleModel, LSTMAttentionModel

def test_lstm_attention_model_output_shape():
    """Test LSTM+Attention model produces correct output shape."""
    n_features = 140
    seq_len = 10
    batch_size = 4
    model = LSTMAttentionModel(n_features=n_features)
    x = torch.randn(batch_size, seq_len, n_features)
    output = model(x)
    assert output.shape == (batch_size, 3)

def test_ensemble_predict_no_models():
    """Test ensemble returns HOLD when no models are loaded."""
    ensemble = EnsembleModel()
    obs = np.random.randn(140)
    direction, confidence, per_algo = ensemble.predict(obs)
    assert direction == 0
    assert confidence == 0.0
    assert per_algo == {}

def test_ensemble_weighted_voting(monkeypatch):
    """Test ensemble voting logic with mocked sub-models."""
    ensemble = EnsembleModel()

    # Mock PPO prediction (0=buy)
    class MockPPO:
        def predict(self, obs, deterministic):
            return 0, None
    ensemble._ppo_model = MockPPO()

    # Mock LSTM prediction (1=sell)
    class MockLSTM:
        def __init__(self):
            self.device = torch.device("cpu")
        def __call__(self, seq):
            # Disagree strongly: [buy, sell, hold] -> logits that make buy small
            return torch.tensor([[-10.0, 10.0, -10.0]])
        def to(self, device):
            return self
        def eval(self):
            pass
    ensemble.lstm_model = MockLSTM()

    # Set equal weights
    ensemble.weights = {"ppo": 0.5, "lstm": 0.5, "dreamer": 0.0}

    obs = np.random.randn(140)
    seq = torch.randn(10, 140)

    # PPO votes BUY (idx 0), prob [1, 0, 0]
    # LSTM votes SELL (idx 1), prob [0, 1, 0]
    # Blended: 0.5 * [1, 0, 0] + 0.5 * [0, 1, 0] = [0.5, 0.5, 0]
    # argmax is 0 (BUY) because of tie-breaking (usually first idx)
    # confidence 0.5

    # Since confidence 0.5 < 0.6 consensus threshold, should return HOLD (0)
    direction, confidence, per_algo = ensemble.predict(obs, seq=seq)
    assert direction == 0
    assert pytest.approx(confidence, rel=1e-3) == 0.5

    # Now make them agree on BUY
    class MockLSTM_BUY:
        def __init__(self):
            self.device = torch.device("cpu")
        def __call__(self, seq):
            # Large positive logit for BUY
            return torch.tensor([[10.0, -10.0, -10.0]])
        def to(self, device):
            return self
        def eval(self):
            pass
    ensemble.lstm_model = MockLSTM_BUY()

    ensemble.weights = {"ppo": 0.5, "lstm": 0.5, "dreamer": 0.0}
    direction, confidence, per_algo = ensemble.predict(obs, seq=seq)
    assert direction == 1 # Buy
    assert confidence == 1.0
