"""
Unit tests for production model stubs.
Ensures all models implement the BaseModel interface correctly.
"""

import numpy as np
import pytest
from src.models.base import BaseModel, Signal
from src.models.ppo_agent import PPOAgent
from src.models.lstm_model import LSTMModel
from src.models.dreamer_agent import DreamerAgent


def test_ppo_agent_interface():
    agent = PPOAgent()
    assert isinstance(agent, BaseModel)

    # Test predict with mock features
    features = np.zeros((10,))
    signal = agent.predict(features)
    assert isinstance(signal, Signal)
    assert signal.direction in [0, 1, -1]
    assert 0.0 <= signal.confidence <= 1.0


def test_lstm_model_interface():
    model = LSTMModel(input_dim=10)
    assert isinstance(model, BaseModel)

    # Test predict with mock features
    # LSTM expects (B, T, F) or (T, F)
    features = np.zeros((5, 10))
    signal = model.predict(features)
    assert isinstance(signal, Signal)
    assert signal.direction in [0, 1, -1]
    assert 0.0 <= signal.confidence <= 1.0


def test_dreamer_agent_interface():
    agent = DreamerAgent()
    assert isinstance(agent, BaseModel)

    # Test predict
    features = np.zeros((10,))
    signal = agent.predict(features)
    assert isinstance(signal, Signal)
    assert signal.direction == 0
    assert signal.confidence == 0.0
