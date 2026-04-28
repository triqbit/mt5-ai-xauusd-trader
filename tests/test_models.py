"""Tests for ensemble and PPO models."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import gymnasium as gym
import numpy as np
import pytest
import torch

from src.models.ensemble import EnsembleModel, LSTMAttentionModel
from src.models.ppo_agent import PPOAgent


@pytest.fixture
def obs() -> np.ndarray:
    """Fixture for observation."""
    return np.random.randn(142).astype(np.float32)


@pytest.fixture
def seq() -> torch.Tensor:
    """Fixture for sequence data."""
    return torch.randn(1, 60, 140)


def test_lstm_attention_forward() -> None:
    """Test LSTM-Attention model forward pass."""
    model = LSTMAttentionModel(n_features=140, hidden_size=64, num_layers=1)
    x = torch.randn(8, 60, 140)
    out = model(x)
    assert out.shape == (8, 3)


def test_ensemble_predict_no_models() -> None:
    """Test ensemble prediction with no models loaded."""
    ensemble = EnsembleModel(device="cpu")
    obs = np.random.randn(142)
    direction, confidence, per_algo = ensemble.predict(obs)
    assert direction == 0
    assert confidence == 0.0
    assert per_algo == {}


@patch("src.models.ppo_agent.logging")
def test_ppo_agent_init(mock_logging: MagicMock) -> None:
    """Test PPO agent initialization."""
    # Create a real Box space to avoid DummyVecEnv/obs_space_info issues
    obs_space = gym.spaces.Box(low=-1, high=1, shape=(142,))
    action_space = gym.spaces.Discrete(3)

    mock_env = MagicMock(spec=gym.Env)
    mock_env.observation_space = obs_space
    mock_env.action_space = action_space
    mock_env.reset.return_value = (obs_space.sample(), {})

    # Mock PPO to avoid heavy initialization
    with patch("stable_baselines3.PPO") as mock_ppo:
        agent = PPOAgent(mock_env)
        assert agent.model is not None
        mock_ppo.assert_called_once()


def test_ensemble_record_return() -> None:
    """Test ensemble return recording and weight rebalancing."""
    ensemble = EnsembleModel(device="cpu")
    # Record 50 returns to trigger rebalance
    for _ in range(50):
        ensemble.record_return("ppo", 0.01)
        ensemble.record_return("lstm", 0.02)
        ensemble.record_return("dreamer", 0.005)

    assert ensemble.weights["lstm"] > ensemble.weights["dreamer"]


def test_ensemble_load_ppo() -> None:
    """Test loading PPO model in ensemble."""
    ensemble = EnsembleModel(device="cpu")
    with patch("stable_baselines3.PPO.load") as mock_load:
        ensemble.load_ppo(Path("fake_path"))
        mock_load.assert_called_once()


def test_ensemble_load_lstm() -> None:
    """Test loading LSTM model in ensemble."""
    ensemble = EnsembleModel(device="cpu")
    with patch("torch.load") as mock_load:
        mock_load.return_value = LSTMAttentionModel().state_dict()
        ensemble.load_lstm(Path("fake_path"))
        assert ensemble.lstm_model is not None


def test_ensemble_predict_with_lstm(obs: np.ndarray, seq: torch.Tensor) -> None:
    """Test ensemble prediction with LSTM model."""
    ensemble = EnsembleModel(device="cpu")
    # seq is (1, 60, 140), predict unsqueezes to (1, 1, 60, 140) if we are not careful
    # But wait, EnsembleModel.predict calls self.lstm_model(seq.to(self.device).unsqueeze(0))
    # If seq is (1, 60, 140), unsqueeze(0) makes it (1, 1, 60, 140)
    # LSTMAttentionModel expects (batch, seq_len, n_features)
    # So if we pass seq as (60, 140), it becomes (1, 60, 140) which is correct.

    ensemble.lstm_model = LSTMAttentionModel(n_features=140)
    ensemble.lstm_model.eval()

    single_seq = seq[0] # (60, 140)
    direction, confidence, per_algo = ensemble.predict(obs, seq=single_seq)
    assert direction in [-1, 0, 1]
    assert confidence >= 0.0
    assert "lstm" in per_algo


def test_ppo_agent_train() -> None:
    """Test PPO agent training method."""
    mock_env = MagicMock(spec=gym.Env)
    mock_env.observation_space = gym.spaces.Box(low=-1, high=1, shape=(142,))
    mock_env.action_space = gym.spaces.Discrete(3)

    with patch("stable_baselines3.PPO") as mock_ppo_class:
        mock_ppo_instance = mock_ppo_class.return_value
        agent = PPOAgent(mock_env)
        agent.train(total_timesteps=100)
        mock_ppo_instance.learn.assert_called_once_with(total_timesteps=100)
