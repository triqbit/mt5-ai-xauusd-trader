"""
Unit tests for PPOAgent.
"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import numpy as np
import gymnasium as gym
from src.models.ppo_agent import PPOAgent

@pytest.fixture
def mock_env():
    env = gym.make("CartPole-v1", render_mode="rgb_array")
    return env

def test_ppo_agent_init_new(mock_env):
    agent = PPOAgent(env=mock_env, device="cpu")
    assert agent.model is not None

@patch("stable_baselines3.PPO")
def test_ppo_agent_init_load(mock_ppo, mock_env):
    path = Path("test_ppo_agent.zip")
    path.touch()
    agent = PPOAgent(env=mock_env, model_path=path, device="cpu")
    mock_ppo.load.assert_called_once()
    path.unlink()

def test_ppo_agent_predict(mock_env):
    agent = PPOAgent(env=mock_env, device="cpu")
    obs, _ = mock_env.reset()
    action = agent.predict(obs)
    assert action is not None

def test_ppo_agent_train(mock_env):
    agent = PPOAgent(env=mock_env, device="cpu")
    save_path = Path("test_ppo_save.zip")
    agent.train(total_timesteps=100, save_path=save_path)
    assert save_path.exists()
    save_path.unlink()

@patch("stable_baselines3.common.evaluation.evaluate_policy")
def test_ppo_agent_evaluate(mock_eval, mock_env):
    mock_eval.return_value = (100.0, 1.0)
    agent = PPOAgent(env=mock_env, device="cpu")
    results = agent.evaluate(n_eval_episodes=1)
    assert results["mean_reward"] == 100.0
