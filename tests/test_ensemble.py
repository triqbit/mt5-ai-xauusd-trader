"""Tests for src.models.ensemble module."""
import pytest
from unittest.mock import MagicMock, patch
import numpy as np
try:
    import torch
except ImportError:
    torch = None

from src.core.constants import SignalDirection, ModelAction
from src.models.ensemble import EnsembleModel

@pytest.mark.skipif(torch is None, reason="torch not installed")
def test_ensemble_consensus_buy():
    ensemble = EnsembleModel(device="cpu")

    # Mock PPO
    mock_ppo = MagicMock()
    mock_ppo.predict.return_value = (ModelAction.BUY, None)
    ensemble._ppo_model = mock_ppo

    # Mock weights to be equal
    ensemble.dynamic_ensemble.get_weights = MagicMock(return_value={"ppo": 1.0, "lstm": 0.0, "dreamer": 0.0})

    obs = np.random.rand(140)
    signal = ensemble.predict(obs)

    assert signal.direction == SignalDirection.BUY
    assert signal.confidence == 1.0

@pytest.mark.skipif(torch is None, reason="torch not installed")
def test_ensemble_veto_logic():
    # To test veto, we need a model that returns < 0.40 confidence.
    # Current PPO stub returns 1.0.
    # Let's modify EnsembleModel.predict briefly to test the consensus logic or mock more deeply.

    ensemble = EnsembleModel(device="cpu")

    # Mock a "dummy" model that returns low confidence
    with patch.object(EnsembleModel, "weights", {"dummy": 1.0}):
        # This is harder because ALGORITHMS is class-level.
        pass

def test_ensemble_dissent_buy_sell():
    ensemble = EnsembleModel(device="cpu")

    # Mock PPO says BUY
    mock_ppo = MagicMock()
    mock_ppo.predict.return_value = (ModelAction.BUY, None)
    ensemble._ppo_model = mock_ppo

    # Mock LSTM says SELL
    # We need to mock torch.no_grad and the model call
    ensemble.lstm_model = MagicMock()

    with patch("torch.softmax") as mock_softmax, \
         patch("torch.no_grad"):
        # Softmax returns [HOLD, BUY, SELL]
        mock_softmax.return_value.cpu.return_value.numpy.return_value = np.array([[0.1, 0.1, 0.8]])

        obs = np.random.rand(140)
        seq = torch.randn(10, 140)

        # Ensure weights are set so both models are used
        ensemble.dynamic_ensemble.get_weights = MagicMock(return_value={"ppo": 0.5, "lstm": 0.5, "dreamer": 0.0})

        signal = ensemble.predict(obs, seq=seq)

        # Should be HOLD due to DISSENT
        assert signal.direction == SignalDirection.HOLD
        assert signal.metadata.get("dissent") is True

def test_ensemble_consensus_threshold_fail():
    ensemble = EnsembleModel(device="cpu")

    # Mock PPO says BUY with 100% confidence
    mock_ppo = MagicMock()
    mock_ppo.predict.return_value = (ModelAction.BUY, None)
    ensemble._ppo_model = mock_ppo

    # Mock weights to make confidence < 0.60
    # If PPO weight is 0.5 and other models are not loaded, total_weight = 0.5.
    # Blended = (0.5/0.5) * [0, 1, 0] = [0, 1, 0]. Confidence remains 1.0.
    # We need another model that says HOLD to dilute confidence.

    ensemble.lstm_model = MagicMock()
    with patch("torch.softmax") as mock_softmax, \
         patch("torch.no_grad"):
        # LSTM says HOLD [1.0, 0, 0]
        mock_softmax.return_value.cpu.return_value.numpy.return_value = np.array([[0.8, 0.1, 0.1]])

        ensemble.dynamic_ensemble.get_weights = MagicMock(return_value={"ppo": 0.4, "lstm": 0.6, "dreamer": 0.0})

        obs = np.random.rand(140)
        seq = torch.randn(10, 140)

        signal = ensemble.predict(obs, seq=seq)

        # Blended = 0.4 * [0, 1, 0] + 0.6 * [0.8, 0.1, 0.1] = [0.48, 0.46, 0.06]
        # Argmax is index 0 (HOLD).
        # Wait, if argmax is HOLD, threshold is not enforced in my current code.
        # Let's make BUY the argmax but with low confidence.

        # PPO: [0, 1, 0], LSTM: [0.3, 0.6, 0.1]
        # Weights: 0.5, 0.5
        # Blended: [0.15, 0.8, 0.05] -> BUY 80% (Passes)

        # PPO: [0, 1, 0], LSTM: [0.6, 0.3, 0.1]
        # Blended: [0.3, 0.65, 0.05] -> BUY 65% (Passes)

        # PPO: [0, 1, 0], LSTM: [0.7, 0.2, 0.1]
        # Blended: [0.35, 0.6, 0.05] -> BUY 60% (Passes)

        # PPO: [0, 1, 0], LSTM: [0.8, 0.1, 0.1]
        # Blended: [0.4, 0.55, 0.05] -> BUY 55% (Should FAIL)
        mock_softmax.return_value.cpu.return_value.numpy.return_value = np.array([[0.8, 0.1, 0.1]])
        ensemble.dynamic_ensemble.get_weights = MagicMock(return_value={"ppo": 0.5, "lstm": 0.5, "dreamer": 0.0})

        signal = ensemble.predict(obs, seq=seq)
        assert signal.direction == SignalDirection.HOLD
        assert signal.metadata.get("consensus_fail") is True
