import pytest
import numpy as np

# Skip this entire module if torch is not installed
torch = pytest.importorskip("torch")

from unittest.mock import MagicMock, patch
from src.models.ensemble import EnsembleModel

def test_ensemble_voting_partial_models(mock_config):
    model = EnsembleModel(device="cpu")

    # Mock PPO only
    mock_ppo = MagicMock()
    mock_ppo.predict.return_value = (0, None) # 0 = BUY in SB3 PPO if we mapped it so, but EnsembleModel maps 0 -> 1 (BUY)
    model._ppo_model = mock_ppo

    obs = np.zeros(5)
    direction, confidence, per_algo = model.predict(obs)

    assert "ppo" in per_algo
    assert "lstm" not in per_algo
    assert direction == 1 # 0 mapped to 1
    assert confidence == 1.0

def test_ensemble_weight_rebalancing(mock_config):
    model = EnsembleModel(device="cpu")
    model.weights = {"ppo": 0.33, "dreamer": 0.33, "lstm": 0.34}

    # Record excellent performance for PPO, poor for others
    for _ in range(50):
        model.record_return("ppo", 0.02)
        model.record_return("dreamer", -0.01)
        model.record_return("lstm", 0.0)

    # Weights should have rebalanced
    assert model.weights["ppo"] > 0.5
    # The sum of weights is normalized.
    # With raw sharpes: ppo=0.02/eps, dreamer=0, lstm=0
    # After max(s, 0.0) it's same.
    # After floor 0.05:
    # raw: ppo=large, dreamer=0.05, lstm=0.05
    # Then normalized.
    assert model.weights["dreamer"] >= 0.04 # Allow for normalization slight deviation from 0.05
    assert model.weights["lstm"] < 0.34
