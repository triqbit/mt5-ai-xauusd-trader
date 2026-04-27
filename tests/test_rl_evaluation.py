
import numpy as np
import pytest
from src.research.rl_evaluation import RLEvaluator, RandomAgent, EvaluationMetrics, RegimeMetrics
from src.environment.gym_env import TradingEnv

@pytest.fixture
def dummy_data():
    return np.random.randn(200, 5)

@pytest.fixture
def env(dummy_data):
    return TradingEnv(data=dummy_data, window_size=10)

@pytest.fixture
def random_agent(env):
    return RandomAgent(env.action_space)

def test_rlevaluator_metrics(env, random_agent):
    evaluator = RLEvaluator(env, random_agent)
    report = evaluator.run_evaluation(n_episodes=2)

    assert report.agent_name == "RandomAgent"
    assert isinstance(report.overall_metrics, EvaluationMetrics)
    assert report.overall_metrics.total_reward != 0
    assert 0 <= report.overall_metrics.win_rate <= 1.0
    assert report.overall_metrics.stability_score > 0

def test_regime_sensitivity(env, random_agent):
    evaluator = RLEvaluator(env, random_agent)
    # Mock some rewards
    rewards = [0.1, -0.05, 0.2, -0.1, 0.01, 0.02, 0.5, -0.4]
    regimes = evaluator._calculate_regime_sensitivity(rewards)

    assert len(regimes) > 0
    assert any(r.regime_name == "High Vol" for r in regimes)
    assert any(r.regime_name == "Low Vol" for r in regimes)
    for r in regimes:
        assert isinstance(r, RegimeMetrics)

def test_drawdown_calculation(env, random_agent):
    evaluator = RLEvaluator(env, random_agent)
    # Decreasing balance
    balances = [1000, 900, 800, 700]
    rewards = [-10, -10, -10]
    actions = [1, 1, 1]

    metrics = evaluator._calculate_metrics(rewards, actions, balances)
    assert metrics.max_drawdown > 0
    # DD = (1000 - 700) / 1000 = 0.3
    assert pytest.approx(metrics.max_drawdown) == 0.3

def test_turnover_calculation(env, random_agent):
    evaluator = RLEvaluator(env, random_agent)
    rewards = [0.1, 0.1, 0.1]
    balances = [1000, 1010, 1020]

    # No action changes
    actions = [1, 1, 1]
    metrics = evaluator._calculate_metrics(rewards, actions, balances)
    assert metrics.turnover == 0.0

    # Frequent action changes
    actions = [1, 2, 1]
    metrics = evaluator._calculate_metrics(rewards, actions, balances)
    assert metrics.turnover == 1.0 # 2 changes in 2 steps (diff length is 2)
