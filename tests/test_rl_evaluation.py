"""
Unit and integration tests for RL evaluation framework.
"""

import numpy as np
import pytest
from src.research.rl_evaluation import (
    RLEvaluator,
    MomentumBaseline,
    StabilityMetrics,
    DrawdownMetrics,
    TurnoverMetrics,
    RegimeSensitivity
)
from src.environment.gym_env import TradingEnv


# ── Mock Objects ─────────────────────────────────────────────────────────

class MockAgent:
    def predict(self, observation):
        return 1  # Always buy

# ── Unit Tests ───────────────────────────────────────────────────────────

def test_stability_calculation():
    # Test with custom periods_per_year
    evaluator = RLEvaluator(env=None, periods_per_year=100)
    rewards = [0.1, 0.2, -0.1, 0.3, -0.2]

    metrics = evaluator._calculate_stability(rewards)

    assert isinstance(metrics, StabilityMetrics)
    assert metrics.win_rate == 0.6
    # Sharpe = (0.06 / 0.185) * 10 approx 3.24
    assert metrics.sharpe_ratio > 0

def test_drawdown_calculation():
    evaluator = RLEvaluator(env=None)
    balances = [10000.0, 10500.0, 10200.0, 10800.0, 10100.0]

    metrics = evaluator._calculate_drawdown(balances)

    assert isinstance(metrics, DrawdownMetrics)
    assert metrics.max_drawdown > 0
    assert pytest.approx(metrics.max_drawdown, 0.01) == 0.0648

def test_turnover_calculation():
    # Mock env with initial balance
    class Dummy:
        initial_balance = 10000.0
        commission = 0.0002

    evaluator = RLEvaluator(env=Dummy())
    actions = [1, 1, 0, 2, 2, 0, 1]
    infos = [{"commission": 2.0} if i == 6 else {} for i in range(7)]
    total_steps = 7

    metrics = evaluator._calculate_turnover(actions, infos, total_steps)

    assert isinstance(metrics, TurnoverMetrics)
    assert metrics.total_trades == 2
    assert metrics.total_cost_paid == 2.0 # From info

def test_momentum_baseline():
    baseline = MomentumBaseline()
    obs = np.zeros(10)
    obs[-3] = 100.0
    obs[-8] = 90.0

    assert baseline.predict(obs) == 1

    obs[-3] = 80.0
    assert baseline.predict(obs) == 2

def test_regime_sensitivity_logic():
    evaluator = RLEvaluator(env=None, periods_per_year=1)
    # Generate some synthetic rewards
    # First 30: low vol, positive
    # Next 30: high vol, negative
    rewards = [0.01] * 30 + [0.1, -0.1] * 15

    metrics = evaluator._calculate_regime_sensitivity(rewards)

    assert isinstance(metrics, RegimeSensitivity)
    # Ranging (low vol) should have higher Sharpe than Trending (high vol, mixed) in this case
    assert metrics.ranging_sharpe != metrics.trending_sharpe

# ── Integration Tests ────────────────────────────────────────────────────

def test_evaluator_integration():
    data = np.random.randn(100, 5)
    env = TradingEnv(data)
    evaluator = RLEvaluator(env, n_eval_episodes=2)
    agent = MockAgent()

    report = evaluator.run_evaluation(agent, "MockAgent")

    assert report.agent_name == "MockAgent"
    assert report.total_steps > 0
    assert isinstance(report.stability, StabilityMetrics)
    assert isinstance(report.drawdown, DrawdownMetrics)
    assert report.regime_sensitivity is not None
    assert "total" in report.reward_decomposition
