"""
Tests for RL evaluation framework.
"""

import pytest
import numpy as np
from typing import Dict, Any, Tuple
import gymnasium as gym

from src.research.rl_evaluation import RLEvaluator, EpisodeMetrics, RLPerformanceReport

class MockEnv:
    """Mock environment for testing RLEvaluator."""
    def __init__(self):
        self.action_space = gym.spaces.Discrete(3)
        self.initial_balance = 10000.0
        self.balance = 10000.0
        self.current_step = 0
        # Mock data with trends to test regime detection
        self.data = np.zeros((100, 5))
        self.data[:, 3] = np.linspace(100, 110, 100) # Upward trend
        self.entry_price = 100.0

    def reset(self, seed=None) -> Tuple[np.ndarray, Dict]:
        self.balance = self.initial_balance
        self.current_step = 25 # Start later to allow SMA calculation
        return np.zeros(10), {"balance": self.balance}

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        self.current_step += 1
        reward = 0.1 if action == 1 else -0.05
        self.balance += reward * 100

        terminated = self.current_step >= 50
        truncated = False
        info = {
            "balance": self.balance,
            "total_pnl": self.balance - self.initial_balance,
            "position": 1.0 if action == 1 else 0.0
        }
        return np.zeros(10), reward, terminated, truncated, info

class MockAgent:
    """Mock RL agent for testing RLEvaluator."""
    def predict(self, obs: np.ndarray, deterministic: bool = True) -> int:
        return 1 # Always buy

def test_rl_evaluator_initialization():
    env = MockEnv()
    agent = MockAgent()
    evaluator = RLEvaluator(env, agent)
    assert evaluator.env == env
    assert evaluator.agent == agent

def test_rl_evaluator_run_episode():
    env = MockEnv()
    agent = MockAgent()
    evaluator = RLEvaluator(env, agent)

    metrics, history = evaluator._run_episode()
    assert isinstance(metrics, EpisodeMetrics)
    assert metrics.total_reward > 0
    assert len(history) > 0
    assert history[0]["regime"] in ["Ranging", "Trending Up", "Trending Down", "Unknown"]

def test_rl_evaluator_evaluate():
    env = MockEnv()
    agent = MockAgent()
    evaluator = RLEvaluator(env, agent)

    report = evaluator.evaluate(n_episodes=2)
    assert isinstance(report, RLPerformanceReport)
    assert len(report.episodes) == 2
    assert len(report.regime_analysis) > 0
    assert "SupervisedSim" in report.comparison_baselines

def test_rl_evaluator_baselines():
    env = MockEnv()
    agent = MockAgent()
    evaluator = RLEvaluator(env, agent)

    baselines = evaluator._evaluate_baselines()
    assert "BuyAndHold" in baselines
    assert "Random" in baselines
    assert "SupervisedSim" in baselines
    assert isinstance(baselines["SupervisedSim"], float)
