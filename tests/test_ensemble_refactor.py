try:
    import torch
except ImportError:
    torch = None
import pytest

pytestmark = pytest.mark.skipif(torch is None, reason="torch not installed")

from unittest.mock import MagicMock

import numpy as np

# Use the standardized SignalDirection from constants
from src.core.constants import SignalDirection
from src.models.ensemble import EnsembleModel, LSTMAttentionModel


def test_lstm_attention_model_output_shape():
    """Verify LSTM+Attention model produces correct logit shapes."""
    n_features = 140
    model = LSTMAttentionModel(n_features=n_features)
    # Batch size 2, Sequence length 10, Features 140
    x = torch.randn(2, 10, n_features)
    output = model(x)
    assert output.shape == (2, 3) # [buy, sell, hold] logits

def test_ensemble_model_standardized_direction():
    """Verify EnsembleModel maps Action indices to standard SignalDirection."""
    ensemble = EnsembleModel(device="cpu")

    # Mock the internal models
    mock_ppo = MagicMock()
    # PPO returns index 0 (BUY), 1 (SELL), 2 (HOLD) in legacy logic
    mock_ppo.predict.return_value = (0, None)
    ensemble._ppo_model = mock_ppo

    obs = np.random.rand(5) # Mock observation
    # Adjust ModelAction to ensure prediction is BUY
    # ModelAction.BUY is 1. PPO returns action index.
    mock_ppo.predict.return_value = (1, None)
    signal = ensemble.predict(obs)

    assert isinstance(signal.direction, SignalDirection)
    assert signal.direction == SignalDirection.BUY
    assert signal.metadata["per_algo_votes"]["ppo"] == 1.0

def test_ensemble_record_return_rebalance():
    """Verify weight rebalancing logic triggers correctly."""
    ensemble = EnsembleModel(device="cpu")
    initial_weights = ensemble.weights.copy()

    # Record 50 returns to trigger _rebalance_weights
    # Also mock confidences to avoid calibration penalty
    for _ in range(50):
        # We need to fill _last_confidences to avoid NaN/Zero calibration errors
        ensemble._last_confidences["ppo"].append(0.6)
        ensemble._last_confidences["lstm"].append(0.6)
        ensemble._last_confidences["dreamer"].append(0.6)

        ensemble.record_return("ppo", 0.01)  # Profitable
        ensemble.record_return("lstm", -0.01)  # Losing
        ensemble.record_return("dreamer", 0.0)

    new_weights = ensemble.weights
    assert new_weights["ppo"] > initial_weights["ppo"]
    assert new_weights["lstm"] < initial_weights["lstm"]
