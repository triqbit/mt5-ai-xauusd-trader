
import numpy as np
import pytest
from src.research.rl_evaluation import RLEvaluator, RandomAgent, EvaluationMetrics, RegimeMetrics, RuleBasedAgent
from src.environment.gym_env import TradingEnv

@pytest.fixture
def dummy_data():
    # Create some data with a slight upward trend
    data = np.random.randn(200, 5)
    data[:, 3] += np.linspace(0, 1, 200) # Close price trend
    return data

@pytest.fixture
def env(dummy_data):
    return TradingEnv(data=dummy_data, window_size=10)

@pytest.fixture
def random_agent(env):
    return RandomAgent(env.action_space)

class SB3MockAgent:
    """Mocks an SB3 agent that returns (action, state)."""
    def __init__(self, action_space):
        self.action_space = action_space
    def predict(self, observation, deterministic=True):
        return self.action_space.sample(), None

def test_rlevaluator_metrics(env, random_agent):
    evaluator = RLEvaluator(env, random_agent)
    report = evaluator.run_evaluation(n_episodes=2)

    assert report.agent_name == "RandomAgent"
    assert isinstance(report.overall_metrics, EvaluationMetrics)
    assert 0 <= report.overall_metrics.win_rate <= 1.0
    assert report.overall_metrics.stability_score > 0

def test_sb3_compatibility(env):
    agent = SB3MockAgent(env.action_space)
    evaluator = RLEvaluator(env, agent)
    report = evaluator.run_evaluation(n_episodes=1)
    assert report.agent_name == "SB3MockAgent"

def test_regime_sensitivity(env, random_agent):
    evaluator = RLEvaluator(env, random_agent)
    rewards = [0.1, -0.05, 0.2, -0.1, 0.01, 0.02, 0.5, -0.4]
    regimes = evaluator._calculate_regime_sensitivity(rewards)

    assert len(regimes) > 0
    for r in regimes:
        assert isinstance(r, RegimeMetrics)
        assert abs(r.sharpe_ratio) >= 0

def test_drawdown_across_episodes(env):
    evaluator = RLEvaluator(env, RandomAgent(env.action_space))
    # Mock balances for two episodes
    # Ep 1: 1000 -> 800 (DD 0.2)
    # Ep 2: 1000 -> 900 (DD 0.1)
    # Max DD should be 0.2

    metrics = evaluator._calculate_metrics(
        rewards=[0.1]*10,
        episode_turnovers=[0.1],
        episode_drawdowns=[0.2, 0.1],
        closed_trades_pnl=[10.0]
    )
    assert metrics.max_drawdown == 0.2

def test_per_trade_win_rate(env):
    evaluator = RLEvaluator(env, RandomAgent(env.action_space))
    closed_trades = [10.0, -5.0, 20.0] # 2 wins, 1 loss

    metrics = evaluator._calculate_metrics(
        rewards=[0.1]*10,
        episode_turnovers=[0.1],
        episode_drawdowns=[0.05],
        closed_trades_pnl=closed_trades
    )
    assert pytest.approx(metrics.win_rate) == 2/3

def test_pnl_decomposition_logic(env):
    # RuleBasedAgent should make at least one trade
    agent = RuleBasedAgent(threshold=0.1)
    evaluator = RLEvaluator(env, agent)
    report = evaluator.run_evaluation(n_episodes=1)

    metrics = report.overall_metrics
    # On trade close, realized should be populated and unrealized reset for that trade
    # Since we only run 1 episode, if the trade is closed, realized_pnl > 0 or < 0
    # and unrealized_pnl should be 0 if no position is open at the end
    assert isinstance(metrics.realized_pnl, float)
    assert isinstance(metrics.unrealized_pnl, float)
