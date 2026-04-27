from unittest.mock import MagicMock

import numpy as np
import pytest

from src.models.ensemble import EnsembleModel


def test_ensemble_no_models_loaded():
    model = EnsembleModel(device="cpu")
    # No models loaded (ppo and lstm are None)

    obs = np.random.randn(5)
    direction, confidence, per_algo = model.predict(obs)

    assert direction == 0
    assert confidence == 0.0
    assert per_algo == {}

def test_ensemble_only_ppo_loaded(monkeypatch):
    model = EnsembleModel(device="cpu")

    # Mock PPO model
    mock_ppo = MagicMock()
    mock_ppo.predict.return_value = (0, None) # Action 0 = BUY in SB3?
    # Actually direction_map = {0: 1, 1: -1, 2: 0} in ensemble.py
    # So SB3 action 0 -> direction 1 (BUY)

    model._ppo_model = mock_ppo

    obs = np.random.randn(5)
    direction, confidence, per_algo = model.predict(obs)

    assert direction == 1
    assert confidence == 1.0
    assert "ppo" in per_algo

def test_ensemble_voting_conflict(monkeypatch):
    model = EnsembleModel(device="cpu")

    # Mock PPO to return BUY (action 0)
    mock_ppo = MagicMock()
    mock_ppo.predict.return_value = (0, None)
    model._ppo_model = mock_ppo

    # Mock LSTM to return SELL (action 1)
    # direction_map = {0: 1, 1: -1, 2: 0}
    # For LSTM, it uses softmax.
    model.lstm_model = MagicMock()
    # Mock lstm_model call to return logits that result in SELL
    # logits for [BUY, SELL, HOLD]
    import torch
    model.lstm_model.return_value = torch.tensor([[0.0, 10.0, 0.0]])

    # Weights are equal by default (1/3 each)
    # blended = 1/3 * [1, 0, 0] (PPO) + 1/3 * [0, 1, 0] (LSTM) = [0.33, 0.33, 0]
    # np.argmax will pick the first one with max value

    import torch
    obs = np.random.randn(140)
    seq = torch.randn(1, 10, 140)

    direction, confidence, _per_algo = model.predict(obs, seq=seq)

    # Since weights are equal and PPO is first in iteration?
    # Actually summed. blended = [0.5, 0.5, 0] if we only have 2 models
    assert direction in [1, -1]
    assert pytest.approx(confidence, rel=1e-3) == 0.5
