import pytest
import numpy as np
import torch
from unittest.mock import MagicMock
from src.models.ensemble import EnsembleModel
from src.core.constants import SignalDirection

def test_ensemble_no_models():
    model = EnsembleModel()
    obs = np.random.rand(10)
    direction, confidence, per_algo = model.predict(obs)
    assert direction == SignalDirection.HOLD
    assert confidence == 0.0

def test_ensemble_consensus_threshold():
    model = EnsembleModel(consensus_threshold=0.8)
    # Mock PPO
    mock_ppo = MagicMock()
    mock_ppo.predict.return_value = (1, None) # BUY (if 1 is BUY in ModelAction)
    model._ppo_model = mock_ppo

    # Weights are defaulted. PPO weight might be ~0.33
    # If only PPO is loaded, total_weight = weight_ppo.
    # blended = probs_ppo. argmax = 1. confidence = 1.0.

    obs = np.random.rand(10)
    direction, confidence, per_algo = model.predict(obs)
    # Since confidence 1.0 > 0.8, it should be BUY
    assert direction == SignalDirection.BUY
    assert confidence == 1.0

def test_ensemble_rejection_below_threshold():
    model = EnsembleModel(consensus_threshold=0.9)
    # Mock LSTM with low confidence
    mock_lstm = MagicMock()
    # Mock output logits that yield ~0.4 confidence for BUY
    mock_lstm.side_effect = lambda x: torch.tensor([[0.3, 0.4, 0.3]]) # HOLD, BUY, SELL in ModelAction?
    # Wait, my EnsembleModel uses mapping: 0: HOLD, 1: BUY, 2: SELL
    # logits: [0.3, 0.4, 0.3] -> softmax -> probs approx [0.3, 0.4, 0.3]. Max is index 1 (BUY) with ~0.4.

    model.lstm_model = mock_lstm
    model.dynamic_ensemble.get_weights = MagicMock(return_value={"ppo": 0.0, "dreamer": 0.0, "lstm": 1.0})

    obs = np.random.rand(10)
    seq = torch.rand(5, 140)
    direction, confidence, per_algo = model.predict(obs, seq=seq)

    assert direction == SignalDirection.HOLD
    assert confidence < 0.9
