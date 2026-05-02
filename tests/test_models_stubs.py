import numpy as np

from src.core.constants import SignalDirection
from src.models.base_model import Signal
from src.models.dreamer_agent import DreamerAgent
from src.models.lstm_model import LSTMModel
from src.models.ppo_agent import PPOAgent
from src.trading.trading_env import TradingEnv


def test_ppo_agent_stub():
    # Test initialization without env
    agent = PPOAgent()
    assert agent.model is None

    # Test predict when model is None
    obs = np.zeros((20, 140))
    signal = agent.predict(obs)
    assert isinstance(signal, Signal)
    assert signal.direction == SignalDirection.HOLD
    assert signal.confidence == 0.0


def test_lstm_model_stub():
    agent = LSTMModel(input_dim=10)
    # Even if torch is missing, it should handle gracefully (returning HOLD)
    obs = np.zeros((20, 10))
    signal = agent.predict(obs)
    assert isinstance(signal, Signal)
    if agent.model is not None:
        assert signal.direction in [SignalDirection.BUY, SignalDirection.SELL, SignalDirection.HOLD]
    else:
        assert signal.direction == SignalDirection.HOLD


def test_dreamer_agent_stub():
    agent = DreamerAgent()
    obs = np.zeros((20, 140))
    signal = agent.predict(obs)
    assert isinstance(signal, Signal)
    assert signal.direction == SignalDirection.HOLD
    assert signal.confidence == 0.0


def test_trading_env_skeleton():
    env = TradingEnv()
    obs, info = env.reset()
    assert obs.shape == (20, 140)

    action = 1  # BUY
    obs, reward, _done, _truncated, _info = env.step(action)
    assert obs.shape == (20, 140)
    assert isinstance(reward, float)
