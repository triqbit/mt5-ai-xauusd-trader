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
from src.research.rl_evaluation import (
    MeanReversionBaseline,
    MomentumBaseline,
    RandomBaseline,
    RLEvaluator,
    RLReport,
)


@pytest.fixture
def mock_env_data():
    # Create 200 steps of data to allow for regime detection (needs 100)
    data = np.random.randn(200, 5).astype(np.float32)
    # Add some trend to make it less random
    data[:, 3] = np.linspace(100, 110, 200) # Close price
    return data


@pytest.fixture
def trading_env(mock_env_data):
    return TradingEnv(data=mock_env_data, window_size=10)


def test_rl_evaluator_initialization(trading_env):
    evaluator = RLEvaluator(env=trading_env)
    assert evaluator.env == trading_env
    assert evaluator.annualization_factor == 252


def test_momentum_baseline_predict():
    # Momentum: last > prev + 0.1
    baseline = MomentumBaseline(window=1)
    # n_features=5. last close is at -4. prev close is at -4 - (1*5) = -9
    obs_buy = np.zeros(52)
    obs_buy[-4] = 0.5
    obs_buy[-9] = 0.3
    assert baseline.predict(obs_buy) == 1

    obs_sell = np.zeros(52)
    obs_sell[-4] = -0.5
    obs_sell[-9] = -0.3
    assert baseline.predict(obs_sell) == 2

    obs_hold = np.zeros(52)
    obs_hold[-4] = 0.3
    obs_hold[-9] = 0.3
    assert baseline.predict(obs_hold) == 0


def test_mean_reversion_baseline_predict():
    baseline = MeanReversionBaseline()
    # n_features=5. last close is at -4
    obs_buy = np.zeros(52)
    obs_buy[-4] = -2.1  # Very oversold (< -2.0)
    assert baseline.predict(obs_buy) == 1

    obs_sell = np.zeros(52)
    obs_sell[-4] = 2.1   # Very overbought (> 2.0)
    assert baseline.predict(obs_sell) == 2

    obs_hold = np.zeros(52)
    obs_hold[-4] = 1.5
    assert baseline.predict(obs_hold) == 0


def test_random_baseline_predict():
    baseline = RandomBaseline()
    obs = np.zeros(52)
    for _ in range(10):
        action = baseline.predict(obs)
        assert action in [0, 1, 2]


def test_evaluate_runs_to_completion(trading_env):
    evaluator = RLEvaluator(env=trading_env)

    class SimpleAgent:
        def predict(self, observation):
            # observation format: [..., balance, position]
            # balance is -2, position is -1
            return 1 if observation[-2] > 0 else 0

    report = evaluator.evaluate(SimpleAgent(), agent_name="Test_Agent")

    assert isinstance(report, RLReport)
    assert report.agent_name == "Test_Agent"
    assert report.total_steps > 0
    assert hasattr(report.stability, "sharpe_ratio")
    assert hasattr(report.stability, "profit_factor")
    assert hasattr(report.stability, "expectancy")
    assert hasattr(report.stability, "calmar_ratio")
    assert hasattr(report.stability, "ulcer_index")
    assert hasattr(report.stability, "sqn")
    assert hasattr(report.stability, "win_loss_ratio")
    assert hasattr(report.turnover, "total_trades")
    assert hasattr(report.drawdown, "max_drawdown")
    assert isinstance(report.regime_sensitivity, list)
    assert report.reward_decomposition.total_commissions >= 0


def test_compare_agents(trading_env):
    evaluator = RLEvaluator(env=trading_env)

    class BuyAgent:
        def predict(self, observation):
            return 1

    class SellAgent:
        def predict(self, observation):
            return 2

    comparison = evaluator.compare(
        agents=[BuyAgent(), SellAgent()],
        agent_names=["Buyer", "Seller"],
        baseline_name="Buyer"
    )

    assert comparison.baseline_name == "Buyer"
    assert len(comparison.agent_reports) == 2
    assert comparison.best_agent in ["Buyer", "Seller"]


def test_signal_adapter_compatibility(trading_env):
    from src.core.constants import SignalDirection
    from src.models.base_model import Signal
    evaluator = RLEvaluator(env=trading_env)

    class SignalAgent:
        def predict(self, observation):
            return Signal(direction=SignalDirection.BUY, confidence=0.9)

    # _get_prediction should return 1 for SignalDirection.BUY
    prediction = evaluator._get_prediction(SignalAgent(), np.zeros(52))
    assert prediction == 1


def test_to_report_section(trading_env):
    from src.research.reporting import RLSection
    evaluator = RLEvaluator(env=trading_env)

    class SimpleAgent:
        def predict(self, observation):
            return 0

    comparison = evaluator.compare([SimpleAgent()], ["Simple"], "Simple")
    section = evaluator.to_report_section(comparison)

    assert isinstance(section, RLSection)
    assert section.best_agent == "Simple"
    assert len(section.metrics) == 1


def test_extract_trades():
    evaluator = RLEvaluator(env=MagicMock())
    df = pd.DataFrame({
        "balances": [1000, 1000, 1010, 1010, 1015], # balances[1] is entry step (after reset)
        "positions": [0, 1, 1, 1, 0]
    })
    # Entry at index 1. Exit at index 4.
    # PnL = balances[4] - balances[entry_idx - 1] = balances[4] - balances[0] = 1015 - 1000 = 15.0
    trades = evaluator._extract_trades(df)
    assert len(trades) == 1
    assert trades[0]["pnl"] == 15.0
    assert trades[0]["hold_time"] == 3

    df2 = pd.DataFrame({
        "balances": [1000, 1010, 1020, 1030, 1030],
        "positions": [0, 1, 1, 1, 0]
    })
    # Entry at index 1. Exit at index 4.
    # PnL = balances[4] - balances[0] = 1030 - 1000 = 30.0
    trades2 = evaluator._extract_trades(df2)
    assert len(trades2) == 1
    assert trades2[0]["pnl"] == 30.0
    assert trades2[0]["hold_time"] == 3

    # Multiple trades
    df3 = pd.DataFrame({
        "balances": [1000, 1050, 1050, 1050, 1100],
        "positions": [0, 1, 0, 1, 0]
    })
    # Trade 1: Entry 1, Exit 2. PnL = balances[2] - balances[0] = 1050 - 1000 = 50.0
    # Trade 2: Entry 3, Exit 4. PnL = balances[4] - balances[2] = 1100 - 1050 = 50.0
    trades3 = evaluator._extract_trades(df3)
    assert len(trades3) == 2
    assert trades3[0]["pnl"] == 50.0
    assert trades3[1]["pnl"] == 50.0


def test_calculate_drawdown():
    evaluator = RLEvaluator(env=MagicMock())
    df = pd.DataFrame({
        "balances": [100, 110, 100, 90, 105, 120]
    })
    dd_metrics = evaluator._calculate_drawdown(df)
    # Peak: 110. Drop to 90. Drawdown = (110 - 90) / 110 = 20 / 110 approx 0.1818
    assert dd_metrics.max_drawdown == pytest.approx(20/110)
    assert dd_metrics.max_drawdown_duration == 3 # steps where balance < peak: [100, 90, 105]


def test_reward_decomposition():
    evaluator = RLEvaluator(env=MagicMock())
    df = pd.DataFrame({
        "balances": [1000, 1050],
        "commissions": [0, 10]
    })
    trades = [{"pnl": 50.0, "hold_time": 10}]
    decomp = evaluator._calculate_reward_decomposition(df, trades)
    assert decomp.net_pnl == 50.0
    assert decomp.total_commissions == 10.0
    assert decomp.gross_pnl == 60.0
    assert decomp.commission_drag == pytest.approx(10/60 * 100)
    assert decomp.avg_win == 50.0
    assert decomp.avg_loss == 0.0


def test_advanced_stability_metrics(trading_env):
    evaluator = RLEvaluator(env=trading_env)

    # Need enough steps for VaR (needs > 20)
    class TrendAgent:
        def predict(self, observation):
            return 1 # Just buy to generate some returns

    report = evaluator.evaluate(TrendAgent(), agent_name="Trend")

    assert report.stability.skewness is not None
    assert report.stability.kurtosis is not None
    assert report.stability.var_95 != 0.0
    assert report.stability.cvar_95 != 0.0


def test_profit_concentration():
    evaluator = RLEvaluator(env=MagicMock())
    df = pd.DataFrame({
        "balances": [1000, 1100],
        "commissions": [0, 0]
    })
    # 10 trades, top 1 is 50% of profit
    trades = [{"pnl": 50.0, "hold_time": 1}] + [{"pnl": 5.55, "hold_time": 1}] * 9
    # Total net_pnl = 100 (approx)
    decomp = evaluator._calculate_reward_decomposition(df, trades)

    # top 10% of 10 trades is 1 trade.
    # top_profit = 50.0. net_pnl = 100.0. conc = 0.5
    assert decomp.profit_concentration == pytest.approx(0.5, rel=1e-2)


def test_turnover_metrics():
    evaluator = RLEvaluator(env=MagicMock())
    df = pd.DataFrame({"balances": [1000] * 100})
    trades = [
        {"pnl": 10.0, "hold_time": 5},
        {"pnl": -5.0, "hold_time": 15}
    ]
    turnover = evaluator._calculate_turnover(df, trades)
    assert turnover.total_trades == 2
    assert turnover.avg_hold_time == 10.0
    assert turnover.max_hold_time == 15
    assert turnover.min_hold_time == 5
    assert turnover.trade_frequency == (2/100) * 1000


def test_ulcer_index():
    evaluator = RLEvaluator(env=MagicMock())
    # Equity curve with some drawdowns
    df = pd.DataFrame({
        "balances": [100, 100, 90, 80, 100, 110, 100]
    })
    # Peak 100, DDs: [0, 0, 0.1, 0.2, 0, 0, 0.0909]
    # Squared DDs: [0, 0, 0.01, 0.04, 0, 0, 0.00826]
    # Mean SQ DD: (0.01 + 0.04 + 0.00826) / 7 = 0.05826 / 7 approx 0.00832
    # Ulcer Index = sqrt(0.00832) approx 0.091
    metrics = evaluator._calculate_stability(df, [], 0.2)
    assert metrics.ulcer_index > 0
    assert metrics.ulcer_index == pytest.approx(np.sqrt((0.01 + 0.04 + (10/110)**2) / 7), rel=1e-3)


def test_sqn_calculation():
    evaluator = RLEvaluator(env=MagicMock())
    trades = [
        {"pnl": 10.0, "hold_time": 1},
        {"pnl": 10.0, "hold_time": 1},
        {"pnl": 10.0, "hold_time": 1},
        {"pnl": 10.0, "hold_time": 1},
    ]
    # Mean PnL = 10, StdDev = 0. SQN = (10 / 1e-9) * sqrt(4) = very large
    # Let's use more realistic trades
    trades = [{"pnl": 10.0, "hold_time": 1}, {"pnl": -5.0, "hold_time": 1}]
    # Mean = 2.5, Std = 7.5. SQN = (2.5 / 7.5) * sqrt(2) approx 0.33 * 1.41 = 0.47
    df = pd.DataFrame({"balances": [100, 100, 105]})
    metrics = evaluator._calculate_stability(df, trades, 0.0)
    assert metrics.sqn == pytest.approx((2.5 / 7.5) * np.sqrt(2))
