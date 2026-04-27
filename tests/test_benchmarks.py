"""
Tests for the benchmarking framework.
"""

import numpy as np
import pytest
from src.environment.gym_env import TradingEnv
from src.research.benchmarks import (
    BenchmarkEvaluator,
    EMACrossoverBaseline,
    MomentumBaseline,
    VolatilityBreakoutBaseline,
    NaiveDirectionalBaseline,
    RiskFilteredBaseline,
)

@pytest.fixture
def mock_data():
    # 200 steps, 5 features (OHLCV)
    data = np.random.randn(200, 5)
    # Ensure some trend for EMA/Momentum
    data[:, 3] = np.linspace(100, 110, 200) + np.random.randn(200) * 0.1
    data[:, 0] = data[:, 3] - 0.05 # Open slightly below Close
    return data

@pytest.fixture
def env(mock_data):
    return TradingEnv(data=mock_data, window_size=20)

def test_ema_crossover(env):
    strategy = EMACrossoverBaseline(window_size=20)
    obs, _ = env.reset()
    action = strategy.predict(obs)
    assert action in [0, 1, 2]

def test_momentum(env):
    strategy = MomentumBaseline(window_size=20)
    obs, _ = env.reset()
    action = strategy.predict(obs)
    assert action in [0, 1, 2]

def test_volatility_breakout(env):
    strategy = VolatilityBreakoutBaseline(window_size=20)
    obs, _ = env.reset()
    action = strategy.predict(obs)
    assert action in [0, 1, 2]

def test_naive_directional(env):
    strategy = NaiveDirectionalBaseline(window_size=20)
    obs, _ = env.reset()
    action = strategy.predict(obs)
    assert action in [0, 1, 2]

def test_risk_filtered(env):
    base_strategy = NaiveDirectionalBaseline(window_size=20)
    strategy = RiskFilteredBaseline(base_strategy, min_volatility=0.0)
    obs, _ = env.reset()
    action = strategy.predict(obs)
    assert action in [0, 1, 2]

def test_evaluator(env):
    evaluator = BenchmarkEvaluator(env)
    strategy = NaiveDirectionalBaseline(window_size=20)
    report = evaluator.evaluate(strategy, n_episodes=2)

    assert report.strategy_name == "Naive_Directional"
    assert isinstance(report.cumulative_return, float)
    assert isinstance(report.total_trades, int)
