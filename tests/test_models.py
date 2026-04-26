"""Tests for AI models."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import gymnasium as gym
import numpy as np
import torch

from src.models.ensemble import EnsembleModel, LSTMAttentionModel
from src.models.ppo_agent import PPOAgent
from src.models.transformer_model import TimeSeriesTransformer


def test_lstm_attention_model() -> None:
    """Test LSTMAttentionModel forward pass."""
    model = LSTMAttentionModel(n_features=10, hidden_size=16, n_heads=2)
    x = torch.randn(2, 5, 10)  # batch, seq, features
    out = model(x)
    assert out.shape == (2, 3)


def test_market_transformer() -> None:
    """Test TimeSeriesTransformer forward pass."""
    model = TimeSeriesTransformer(input_dim=10, model_dim=16, num_heads=2)
    x = torch.randn(2, 5, 10)
    out = model(x)
    assert out.shape == (2, 3)


def test_ensemble_model_predict() -> None:
    """Test EnsembleModel prediction logic."""
    ensemble = EnsembleModel()
    obs = np.random.randn(140).astype(np.float32)

    # No models loaded
    direction, confidence, per_algo = ensemble.predict(obs)
    assert direction == 0
    assert confidence == 0.0
    assert per_algo == {}

    # Mock a model
    ensemble.lstm_model = MagicMock()
    ensemble.lstm_model.side_effect = lambda _: torch.tensor([[1.0, 0.0, 0.0]])  # Buy

    # Prediction with LSTM
    seq = torch.randn(10, 140)
    direction, confidence, per_algo = ensemble.predict(obs, seq=seq)
    assert direction == 1
    assert "lstm" in per_algo


def test_ensemble_model_rebalance() -> None:
    """Test EnsembleModel weight rebalancing."""
    ensemble = EnsembleModel()
    # Record some returns
    for _ in range(60):
        ensemble.record_return("ppo", 0.01)
        ensemble.record_return("lstm", -0.01)

    assert ensemble.weights["ppo"] > ensemble.weights["lstm"]


def test_ppo_agent() -> None:
    """Test PPOAgent stub."""

    # Create a real but minimal environment to satisfy SB3 checks
    class MockEnv(gym.Env):
        def __init__(self) -> None:
            super().__init__()
            self.observation_space = gym.spaces.Box(low=-1, high=1, shape=(10,))
            self.action_space = gym.spaces.Discrete(3)

        def reset(self, seed=None, options=None):
            return np.zeros(10).astype(np.float32), {}

    env = MockEnv()
    # Mock SB3 PPO
    with MagicMock() as mock_ppo_class, patch("stable_baselines3.PPO", mock_ppo_class):
        agent = PPOAgent(env)
        assert agent.model is not None

        obs = np.random.randn(10).astype(np.float32)
        agent.model.predict.return_value = (1, None)
        action = agent.predict(obs)
        assert action == 1

        # Test evaluate
        agent.model.get_env.return_value = agent.env
        with patch("stable_baselines3.common.evaluation.evaluate_policy") as mock_eval:
            mock_eval.return_value = (100.0, 10.0)
            metrics = agent.evaluate(n_eval_episodes=5)
            assert metrics["mean_reward"] == 100.0


def test_ensemble_load_errors() -> None:
    """Test error handling in EnsembleModel loading."""
    ensemble = EnsembleModel()
    with patch("stable_baselines3.PPO.load", side_effect=Exception("Load error")):
        ensemble.load_ppo(MagicMock())
        assert ensemble._ppo_model is None


def test_ensemble_load_lstm() -> None:
    """Test LSTM loading in EnsembleModel."""
    ensemble = EnsembleModel()
    with patch("torch.load", return_value={}), patch.object(
        LSTMAttentionModel, "load_state_dict"
    ):
        ensemble.load_lstm(MagicMock())
        assert ensemble.lstm_model is not None
