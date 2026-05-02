import sys
from unittest.mock import MagicMock

# Mock TA-Lib before any other imports
sys.modules["talib"] = MagicMock()

import numpy as np

from src.core.constants import SignalDirection
from src.models.ensemble import EnsembleModel


def test_ensemble_weight_delegation():
    """Verify EnsembleModel delegates weighting to DynamicEnsemble."""
    model = EnsembleModel(device="cpu")

    # Check initial weights via property
    assert "ppo" in model.weights
    assert "dreamer" in model.weights
    assert "lstm" in model.weights
    assert abs(model.weights["ppo"] - 1 / 3) < 1e-5


def test_ensemble_record_return_triggers_rebalance():
    """Verify record_return eventually updates weights via DynamicEnsemble."""
    model = EnsembleModel(device="cpu")

    # Mock update_weights to track calls
    model.dynamic_ensemble.update_weights = MagicMock(
        side_effect=model.dynamic_ensemble.update_weights
    )

    # Record 50 returns for PPO
    for _ in range(50):
        model.record_return("ppo", 0.01)  # positive returns

    assert model.dynamic_ensemble.update_weights.called
    # PPO should have higher weight now
    assert model.weights["ppo"] > 1 / 3


def test_ensemble_predict_uses_weights():
    """Verify predict uses the delegated weights."""
    model = EnsembleModel(device="cpu")

    # Manually set weights in dynamic_ensemble
    model.dynamic_ensemble.weights = {"ppo": 1.0, "dreamer": 0.0, "lstm": 0.0}

    # Mock PPO model
    model._ppo_model = MagicMock()
    # PPO predicts BUY (0 in legacy ensemble mapping)
    model._ppo_model.predict.return_value = (0, None)

    obs = np.random.rand(140)
    direction, confidence, per_algo = model.predict(obs)

    assert direction == SignalDirection.BUY
    assert confidence == 1.0
    assert per_algo["ppo"] == 0
