"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_rl_evaluation.py
Tests for institutional RL evaluation framework.
"""

from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from src.environment.gym_env import TradingEnv
from src.research.rl_evaluation import MomentumBaseline, RLEvaluator, RLReport


@pytest.fixture
def mock_env_data():
    # Create 200 steps of data to allow for regime detection (needs 100)
    data = np.random.randn(200, 5).astype(np.float32)
    # Add some trend to make it less random
    data[:, 3] = np.linspace(100, 110, 200)  # Close price
    return data


@pytest.fixture
def trading_env(mock_env_data):
    return TradingEnv(data=mock_env_data, window_size=10)


def test_rl_evaluator_initialization(trading_env):
    evaluator = RLEvaluator(env=trading_env)
    assert evaluator.env == trading_env
    assert evaluator.annualization_factor == 252


def test_momentum_baseline_predict():
    baseline = MomentumBaseline()
    # Mock observation: [window_normalized, balance, position]
    # last_val is at index -3
    obs_buy = np.zeros(52)
    obs_buy[-3] = 0.6
    assert baseline.predict(obs_buy) == 1

    obs_sell = np.zeros(52)
    obs_sell[-3] = -0.6
    assert baseline.predict(obs_sell) == 2

    obs_hold = np.zeros(52)
    obs_hold[-3] = 0.1
    assert baseline.predict(obs_hold) == 0


def test_evaluate_runs_to_completion(trading_env):
    evaluator = RLEvaluator(env=trading_env)

    class SimpleAgent:
        def predict(self, observation):
            return 1 if observation[-3] > 0 else 0

    report = evaluator.evaluate(SimpleAgent(), agent_name="Test_Agent")

    assert isinstance(report, RLReport)
    assert report.agent_name == "Test_Agent"
    assert report.total_steps > 0
    assert hasattr(report.stability, "sharpe_ratio")
    assert hasattr(report.turnover, "total_trades")
    assert hasattr(report.drawdown, "max_drawdown")
    assert isinstance(report.regime_sensitivity, list)
    assert report.reward_decomposition.total_commissions >= 0


def test_extract_trades():
    evaluator = RLEvaluator(env=MagicMock())
    df = pd.DataFrame({"balances": [1000, 1000, 1010, 1010, 1005], "positions": [0, 1, 1, 0, 0]})
    trades = evaluator._extract_trades(df)
    assert len(trades) == 1
    assert trades[0] == 0.0  # balance[3] - balance[2] = 1010 - 1010

    df2 = pd.DataFrame({"balances": [1000, 1000, 1010, 1020, 1020], "positions": [0, 1, 1, 1, 0]})
    trades2 = evaluator._extract_trades(df2)
    assert len(trades2) == 1
    assert trades2[0] == 0.0  # balance[4] - balance[3] = 1020 - 1020

    # In our env, balance is updated when position is closed.
    # So if positions[i-1] != 0 and positions[i] == 0,
    # the PnL is in balances[i] - balances[i-1]
    df3 = pd.DataFrame({"balances": [1000, 1000, 1000, 1050, 1050], "positions": [0, 1, 1, 0, 0]})
    trades3 = evaluator._extract_trades(df3)
    assert len(trades3) == 1
    assert trades3[0] == 50.0


def test_calculate_drawdown():
    evaluator = RLEvaluator(env=MagicMock())
    df = pd.DataFrame({"balances": [100, 110, 100, 90, 105, 120]})
    dd_metrics = evaluator._calculate_drawdown(df)
    # Peak: 110. Drop to 90. Drawdown = (110 - 90) / 110 = 20 / 110 approx 0.1818
    assert dd_metrics.max_drawdown == pytest.approx(20 / 110)
    assert dd_metrics.max_drawdown_duration == 3  # steps where balance < peak: [100, 90, 105]


def test_reward_decomposition():
    evaluator = RLEvaluator(env=MagicMock())
    df = pd.DataFrame({"balances": [1000, 1050], "commissions": [0, 10]})
    decomp = evaluator._calculate_reward_decomposition(df)
    assert decomp.net_pnl == 50.0
    assert decomp.total_commissions == 10.0
    assert decomp.gross_pnl == 60.0
    assert decomp.commission_drag == pytest.approx(10 / 60 * 100)
