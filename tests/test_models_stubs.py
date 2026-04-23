"""
Verification tests for model stubs.
Ensures all models implement the BaseModel interface correctly.
"""

import unittest.mock as mock
import numpy as np
import pytest
from src.models import BaseModel, Signal, PPOAgent, LSTMModel, DreamerAgent

def test_signal_dataclass():
    sig = Signal(direction=1, confidence=0.8)
    assert sig.direction == 1
    assert sig.confidence == 0.8

@pytest.mark.parametrize("model_class", [PPOAgent, LSTMModel, DreamerAgent])
def test_model_interface(model_class):
    if model_class is None:
        pytest.skip("Model class not available (missing dependencies)")

    model = model_class()

    assert isinstance(model, BaseModel)

    features = np.random.rand(140).astype(np.float32)
    signal = model.predict(features)

    assert isinstance(signal, Signal)
    assert signal.direction in [1, -1, 0]
    assert 0.0 <= signal.confidence <= 1.0

def test_lstm_model_sequence_input():
    if LSTMModel is None:
        pytest.skip("LSTMModel not available")
    model = LSTMModel(input_size=10)
    features = np.random.rand(5, 10).astype(np.float32)  # seq_len=5, n_features=10
    signal = model.predict(features)
    assert isinstance(signal, Signal)

def test_ppo_agent_mapping():
    if PPOAgent is None:
        pytest.skip("PPOAgent not available")
    # We can't easily test the mapping without a loaded model,
    # but we can verify the class structure.
    agent = PPOAgent()
    assert hasattr(agent, 'predict')
    # Default behavior when no model is loaded
    sig = agent.predict(np.random.rand(140))
    assert sig.direction == 0
    assert sig.confidence == 0.0
