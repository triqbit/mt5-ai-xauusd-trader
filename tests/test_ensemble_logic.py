import pytest
import numpy as np
from src.models.ensemble import EnsembleModel
from src.core.constants import SignalDirection

@pytest.fixture
def ensemble():
    return EnsembleModel(device="cpu")

def test_ensemble_low_consensus(ensemble):
    # Mock votes that don't reach 60% consensus
    ensemble.lstm_model = MagicMock()
    ensemble.lstm_model.return_value = MagicMock()

    with patch("torch.no_grad"), patch("torch.softmax") as mock_softmax:
        # Votes [hold=0.45, buy=0.55, sell=0.0] -> BUY is max but 0.55 < 0.60
        mock_softmax.return_value.cpu.return_value.numpy.return_value = [np.array([0.55, 0.0, 0.45])]
        ensemble.dynamic_ensemble.get_weights = MagicMock(return_value={"ppo": 0.0, "dreamer": 0.0, "lstm": 1.0})

        obs = np.random.rand(140)
        seq = MagicMock()
        signal = ensemble.predict(obs, seq=seq)

        assert signal.direction == SignalDirection.HOLD
        assert signal.metadata["reason"] == "low_consensus"

def test_ensemble_consensus_veto_actual(ensemble):
    # Manually trigger predict logic by mocking internal components
    ensemble._ppo_model = MagicMock()
    ensemble._ppo_model.predict.return_value = (1, None) # BUY (index 1)

    # Mocking weights
    ensemble.dynamic_ensemble.get_weights = MagicMock(return_value={"ppo": 1.0, "dreamer": 0.0, "lstm": 0.0})

    # Force a low confidence vote to trigger veto
    # Wait, in predict(), if PPO is loaded:
    # action, _ = self._ppo_model.predict(features, deterministic=True)
    # probs = np.zeros(3); probs[int(action)] = 1.0; votes["ppo"] = probs
    # This always gives 100% confidence for PPO.

    # Let's mock LSTM which has probs
    ensemble.lstm_model = MagicMock()
    ensemble.lstm_model.return_value = MagicMock() # logits

    with patch("torch.no_grad"), patch("torch.softmax") as mock_softmax:
        mock_softmax.return_value = MagicMock()
        mock_softmax.return_value.cpu.return_value.numpy.return_value = [np.array([0.3, 0.3, 0.4])] # buy, sell, hold
        # LSTM votes [hold=0.4, buy=0.3, sell=0.3] -> max is 0.4

        ensemble.dynamic_ensemble.get_weights = MagicMock(return_value={"ppo": 0.0, "dreamer": 0.0, "lstm": 1.0})

        obs = np.random.rand(140)
        seq = MagicMock()
        signal = ensemble.predict(obs, seq=seq)

        # Veto threshold is 0.40. If max(probs) < 0.40, it vetoes.
        # Here max is exactly 0.40, so it should NOT veto if logic is < 0.40.
        assert "veto" not in signal.metadata

        # Now make it 0.39
        mock_softmax.return_value.cpu.return_value.numpy.return_value = [np.array([0.3, 0.31, 0.39])]
        signal = ensemble.predict(obs, seq=seq)
        assert signal.direction == SignalDirection.HOLD
        assert signal.metadata["veto"] == "lstm"

from unittest.mock import MagicMock, patch
