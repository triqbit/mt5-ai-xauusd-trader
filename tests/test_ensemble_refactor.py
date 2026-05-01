from unittest.mock import MagicMock

import numpy as np
import pytest

# Skip if torch is not installed (CI environment)
pytest.importorskip("torch")

from src.core.constants import SignalDirection
from src.models.ensemble import EnsembleModel


def test_ensemble_weight_delegation():
    """Verify EnsembleModel delegates weighting to DynamicEnsemble."""
    model = EnsembleModel(device="cpu")
    assert "ppo" in model.weights
    assert "dreamer" in model.weights
    assert "lstm" in model.weights
    assert abs(model.weights["ppo"] - 1 / 3) < 1e-5


def test_ensemble_record_return_triggers_rebalance():
    """Verify record_return eventually updates weights via DynamicEnsemble."""
    model = EnsembleModel(device="cpu")
    model.dynamic_ensemble.update_weights = MagicMock(
        side_effect=model.dynamic_ensemble.update_weights
    )
    for _ in range(50):
        model.record_return("ppo", 0.01)
    assert model.dynamic_ensemble.update_weights.called
    assert model.weights["ppo"] > 1 / 3


def test_ensemble_predict_uses_weights():
    """Verify predict uses the delegated weights."""
    model = EnsembleModel(device="cpu")
    model.dynamic_ensemble.weights = {"ppo": 1.0, "dreamer": 0.0, "lstm": 0.0}
    model._ppo_model = MagicMock()
    model._ppo_model.predict.return_value = (0, None)
    obs = np.random.rand(140)
    direction, confidence, per_algo = model.predict(obs)
    assert direction == SignalDirection.BUY
    assert confidence == 1.0
    assert per_algo["ppo"] == 0
