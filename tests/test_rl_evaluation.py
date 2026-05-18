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
    # Mock observation: [window_normalized_flattened, balance, position]
    # n_features=5. last close is at -(5+2)+3 = -4
    obs_buy = np.zeros(52)
    obs_buy[-4] = 0.6
    assert baseline.predict(obs_buy) == 1

    obs_sell = np.zeros(52)
    obs_sell[-4] = -0.6
    assert baseline.predict(obs_sell) == 2

    obs_hold = np.zeros(52)
    obs_hold[-4] = 0.1
    assert baseline.predict(obs_hold) == 0


def test_mean_reversion_baseline_predict():
    baseline = MeanReversionBaseline()
    # n_features=5. last close is at -4
    obs_buy = np.zeros(52)
    obs_buy[-4] = -2.0  # Very oversold
    assert baseline.predict(obs_buy) == 1

    obs_sell = np.zeros(52)
    obs_sell[-4] = 2.0  # Very overbought
    assert baseline.predict(obs_sell) == 2

    obs_hold = np.zeros(52)
    obs_hold[-4] = 0.5
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
            return 1 if observation[-3] > 0 else 0

    report = evaluator.evaluate(SimpleAgent(), agent_name="Test_Agent")

    assert isinstance(report, RLReport)
    assert report.agent_name == "Test_Agent"
    assert report.total_steps > 0
    assert hasattr(report.stability, "sharpe_ratio")
    assert hasattr(report.stability, "profit_factor")
    assert hasattr(report.stability, "expectancy")
    assert hasattr(report.stability, "calmar_ratio")
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
        agents=[BuyAgent(), SellAgent()], agent_names=["Buyer", "Seller"], baseline_name="Buyer"
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
    assert hasattr(section.metrics[0], "lake_ratio")
    assert hasattr(section.metrics[0], "portfolio_heat")

    # New fields
    assert hasattr(section.metrics[0], "trade_frequency")
    assert hasattr(section.metrics[0], "avg_hold_time")
    assert hasattr(section.metrics[0], "action_entropy")
    assert hasattr(section.metrics[0], "commission_drag")
    assert hasattr(section.metrics[0], "profit_concentration")
    assert hasattr(section.metrics[0], "regime_stability")
    assert hasattr(section.metrics[0], "mae_avg")
    assert hasattr(section.metrics[0], "mfe_avg")
    assert hasattr(section.metrics[0], "p_value")
    assert hasattr(section.metrics[0], "session_diversification")
    assert hasattr(section.metrics[0], "flip_flop_rate")


def test_to_report_section_population(trading_env):
    from src.research.rl_evaluation import RLEvaluator

    evaluator = RLEvaluator(env=trading_env)

    class SimpleAgent:
        def predict(self, observation):
            return 1 if np.random.rand() > 0.5 else 0

    comparison = evaluator.compare([SimpleAgent()], ["Agent1"], "Agent1")
    section = evaluator.to_report_section(comparison)

    metric = section.metrics[0]
    # Check that new metrics are not just default 0.0 if there's activity
    # (Note: depending on random data, some might still be 0, but we check existence)
    assert metric.trade_frequency >= 0.0
    assert metric.avg_hold_time >= 0.0
    assert metric.action_entropy >= 0.0
    assert metric.commission_drag >= 0.0
    assert metric.profit_concentration >= 0.0
    assert metric.regime_stability >= 0.0


def test_extract_trades():
    evaluator = RLEvaluator(env=MagicMock())
    df = pd.DataFrame(
        {
            "balances": [1000, 1000, 1010, 1010, 1015],  # balances[1] is entry step (after reset)
            "positions": [0, 1, 1, 1, 0],
        }
    )
    # Entry at index 1. Exit at index 4.
    # PnL = balances[4] - balances[entry_idx - 1] = balances[4] - balances[0] = 1015 - 1000 = 15.0
    trades = evaluator._extract_trades(df)
    assert len(trades) == 1
    assert trades[0]["pnl"] == 15.0
    assert trades[0]["hold_time"] == 3

    df2 = pd.DataFrame({"balances": [1000, 1010, 1020, 1030, 1030], "positions": [0, 1, 1, 1, 0]})
    # Entry at index 1. Exit at index 4.
    # PnL = balances[4] - balances[0] = 1030 - 1000 = 30.0
    trades2 = evaluator._extract_trades(df2)
    assert len(trades2) == 1
    assert trades2[0]["pnl"] == 30.0
    assert trades2[0]["hold_time"] == 3

    # Multiple trades
    df3 = pd.DataFrame({"balances": [1000, 1050, 1050, 1050, 1100], "positions": [0, 1, 0, 1, 0]})
    # Trade 1: Entry 1, Exit 2. PnL = balances[2] - balances[0] = 1050 - 1000 = 50.0
    # Trade 2: Entry 3, Exit 4. PnL = balances[4] - balances[2] = 1100 - 1050 = 50.0
    trades3 = evaluator._extract_trades(df3)
    assert len(trades3) == 2
    assert trades3[0]["pnl"] == 50.0
    assert trades3[1]["pnl"] == 50.0


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
    trades = [{"pnl": 50.0, "hold_time": 10}]
    decomp = evaluator._calculate_reward_decomposition(df, trades)
    assert decomp.net_pnl == 50.0
    assert decomp.total_commissions == 10.0
    assert decomp.gross_pnl == 60.0
    assert decomp.commission_drag == pytest.approx(10 / 60 * 100)
    assert decomp.avg_win == 50.0
    assert decomp.avg_loss == 0.0


def test_advanced_stability_metrics(trading_env):
    evaluator = RLEvaluator(env=trading_env)

    # Need enough steps for VaR (needs > 20)
    # Also need some variation for SQN (at least one trade)
    class TrendAgent:
        def __init__(self):
            self.step = 0

        def predict(self, observation):
            self.step += 1
            if self.step < 10:
                return 1  # Buy
            if self.step == 10:
                return 2  # Close
            if self.step == 20:
                return 1  # Buy again
            if self.step == 30:
                return 2  # Close again
            return 0

    report = evaluator.evaluate(TrendAgent(), agent_name="Trend")

    assert report.stability.skewness is not None
    assert report.stability.kurtosis is not None
    assert report.stability.var_95 is not None
    assert report.stability.cvar_95 is not None
    assert report.stability.ulcer_index >= 0.0
    assert report.stability.sqn is not None
    assert report.stability.tail_ratio >= 0.0
    assert report.stability.common_sense_ratio >= 0.0
    assert report.stability.gain_to_pain_ratio >= 0.0


def test_robustness_to_high_feature_count():
    # Test that evaluate handles data with > 5 features correctly
    data10 = np.random.randn(200, 10).astype(np.float32)
    data10[:, 3] = np.linspace(100, 110, 200)
    env = TradingEnv(data=data10, window_size=10)
    evaluator = RLEvaluator(env=env, n_features=10)

    class HoldAgent:
        def predict(self, obs):
            return 0

    # This should not raise ValueError when creating df_slice in evaluate
    report = evaluator.evaluate(HoldAgent())
    assert report.agent_name == "RL_Agent"


def test_get_prediction_robustness():
    evaluator = RLEvaluator(env=MagicMock())

    class MultiAgent:
        def predict(self, obs):
            if obs[0] == 1:
                return (np.array([1]), {"info": "sb3"})
            if obs[0] == 2:
                return [2, 0]
            if obs[0] == 3:
                from src.core.constants import SignalDirection
                from src.models.base_model import Signal

                return Signal(direction=SignalDirection.SELL, confidence=0.8)
            if obs[0] == 4:

                class MockEnum:
                    value = 1

                return MockEnum()
            if obs[0] == 5:
                return -1  # Test explicit SELL mapping
            return 0

    assert evaluator._get_prediction(MultiAgent(), np.array([1])) == 1
    assert evaluator._get_prediction(MultiAgent(), np.array([2])) == 2
    # SignalDirection.SELL is -1. The environment's action for SELL is 2.
    assert evaluator._get_prediction(MultiAgent(), np.array([3])) == 2
    assert evaluator._get_prediction(MultiAgent(), np.array([4])) == 1
    assert evaluator._get_prediction(MultiAgent(), np.array([5])) == 2
    assert evaluator._get_prediction(MultiAgent(), np.array([0])) == 0


def test_profit_concentration():
    evaluator = RLEvaluator(env=MagicMock())
    df = pd.DataFrame({"balances": [1000, 1100], "commissions": [0, 0]})
    # 10 trades, top 1 is 50% of profit
    trades = [{"pnl": 50.0, "hold_time": 1}] + [{"pnl": 5.55, "hold_time": 1}] * 9
    # Total net_pnl = 100 (approx)
    decomp = evaluator._calculate_reward_decomposition(df, trades)

    # top 10% of 10 trades is 1 trade.
    # top_profit = 50.0. net_pnl = 100.0. conc = 0.5
    assert decomp.profit_concentration == pytest.approx(0.5, rel=1e-2)


def test_sb3_model_prediction_support(trading_env):
    evaluator = RLEvaluator(env=trading_env)

    class MockSB3Model:
        def predict(self, obs, state=None, episode_start=None, deterministic=False):
            # SB3 returns (action, next_state)
            return np.array([1]), None

    prediction = evaluator._get_prediction(MockSB3Model(), np.zeros(52))
    assert prediction == 1


def test_parameterized_indices(mock_env_data):
    # Data with 6 features, close at index 4
    data6 = np.random.randn(200, 6).astype(np.float32)
    data6[:, 4] = np.linspace(100, 110, 200)

    env = TradingEnv(data=data6, window_size=10)
    RLEvaluator(env=env, close_idx=4, n_features=6)

    # Momentum baseline should also use these
    baseline = MomentumBaseline(close_idx=4, n_features=6)

    # obs size: 10 * 6 + 2 = 62
    obs_buy = np.zeros(62)
    # last_close_idx = -(6+2) + 4 = -4. (Wait, let's check logic)
    # n_features=6. balance is -2, pos is -1.
    # last step features: -(6+2) to -3.
    # index 0: -8, 1: -7, 2: -6, 3: -5, 4: -4, 5: -3.
    # Yes, index 4 is -4.
    obs_buy[-4] = 0.6
    assert baseline.predict(obs_buy) == 1


def test_turnover_metrics():
    evaluator = RLEvaluator(env=MagicMock())
    df = pd.DataFrame({"balances": [1000] * 100, "actions": [0, 1, 2, 0] * 25})
    trades = [{"pnl": 10.0, "hold_time": 5}, {"pnl": -5.0, "hold_time": 15}]
    turnover = evaluator._calculate_turnover(df, trades)
    assert turnover.total_trades == 2
    assert turnover.avg_hold_time == 10.0
    assert turnover.max_hold_time == 15
    assert turnover.min_hold_time == 5
    assert turnover.trade_frequency == (2 / 100) * 1000
    assert turnover.action_entropy > 0.0


def test_regime_stability_metric():
    from src.models.regime_detector import MarketRegime
    from src.research.rl_evaluation import RegimePerformance

    evaluator = RLEvaluator(env=MagicMock())

    # High consistency
    regime_perf_stable = [
        RegimePerformance(
            regime=MarketRegime.TRENDING,
            sharpe_ratio=2.0,
            win_rate=0.6,
            total_trades=10,
            profit_factor=2.0,
        ),
        RegimePerformance(
            regime=MarketRegime.RANGING,
            sharpe_ratio=1.9,
            win_rate=0.55,
            total_trades=10,
            profit_factor=1.8,
        ),
    ]
    stability_stable = evaluator._calculate_stability(
        pd.DataFrame({"balances": [100, 110, 120]}), [], 0.05, regime_perf_stable
    )

    # Low consistency
    regime_perf_unstable = [
        RegimePerformance(
            regime=MarketRegime.TRENDING,
            sharpe_ratio=5.0,
            win_rate=0.8,
            total_trades=10,
            profit_factor=4.0,
        ),
        RegimePerformance(
            regime=MarketRegime.RANGING,
            sharpe_ratio=0.1,
            win_rate=0.4,
            total_trades=10,
            profit_factor=1.0,
        ),
    ]
    stability_unstable = evaluator._calculate_stability(
        pd.DataFrame({"balances": [100, 110, 120]}), [], 0.05, regime_perf_unstable
    )

    assert stability_stable.regime_stability_score > stability_unstable.regime_stability_score


def test_lake_ratio_calculation():
    evaluator = RLEvaluator(env=MagicMock())
    # 50% drawdown for all steps
    df = pd.DataFrame({"balances": [100, 50, 50, 50]})
    # peak: 100. drawdowns: [0, 0.5, 0.5, 0.5]
    # lake ratio = mean(drawdowns) = 1.5 / 4 = 0.375
    stability = evaluator._calculate_stability(df, [], 0.5)
    assert stability.lake_ratio == pytest.approx(0.375)


def test_exposure_metrics():
    evaluator = RLEvaluator(env=MagicMock())
    df = pd.DataFrame({"positions": [0, 1, 1, 0, 2]})
    exposure = evaluator._calculate_exposure(df)
    # Positions: [0, 1, 1, 0, 2]
    # mean abs: (0+1+1+0+2)/5 = 0.8
    # max: 2
    # time at risk: 3/5 = 60%
    assert exposure.avg_portfolio_heat == 0.8
    assert exposure.max_portfolio_heat == 2.0
    assert exposure.time_at_risk_pct == 60.0


def test_risk_adjusted_pnl():
    evaluator = RLEvaluator(env=MagicMock())
    df = pd.DataFrame({"balances": [1000, 1100], "commissions": [0, 10]})
    # net_pnl = 100. gross = 110. comm = 10.
    # risk_adjusted_pnl = 100 - 0.1 * vol * 1000
    # if vol = 0.5, penalty = 50. adjusted = 50.
    decomp = evaluator._calculate_reward_decomposition(df, [], volatility=0.5)
    assert decomp.risk_adjusted_pnl == 50.0


def test_supervised_baseline():
    from src.research.rl_evaluation import SupervisedBaseline

    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([1])
    baseline = SupervisedBaseline(mock_model)

    obs = np.random.randn(52)
    assert baseline.predict(obs) == 1
    mock_model.predict.assert_called_once()


def test_extract_trades_at_step_0():
    # Test bug fix: position open at step 0
    evaluator = RLEvaluator(env=MagicMock())
    df = pd.DataFrame({"balances": [1000, 1010, 1005], "positions": [1, 1, 0]})
    # Trade from 0 to 2. PnL = balances[2] - balances[0] = 1005 - 1000 = 5.0
    trades = evaluator._extract_trades(df)
    assert len(trades) == 1
    assert trades[0]["pnl"] == 5.0
    assert trades[0]["hold_time"] == 2


def test_empty_dataframe_handling():
    evaluator = RLEvaluator(env=MagicMock())
    df = pd.DataFrame(columns=["balances", "positions", "actions", "commissions"])

    # These should not crash
    drawdown = evaluator._calculate_drawdown(df)
    assert drawdown.max_drawdown == 0.0

    turnover = evaluator._calculate_turnover(df, [])
    assert turnover.total_trades == 0

    exposure = evaluator._calculate_exposure(df)
    assert exposure.avg_portfolio_heat == 0.0

    decomp = evaluator._calculate_reward_decomposition(df, [])
    assert decomp.net_pnl == 0.0


def test_calculate_mae_mfe():
    evaluator = RLEvaluator(env=MagicMock())
    # Long trade with volatility
    df = pd.DataFrame(
        {
            "balances": [1000, 1000, 1010, 990, 1020, 1020],
            "positions": [0, 1, 1, 1, 1, 0],
            "prices": [100, 100, 110, 90, 120, 120],
        }
    )
    # Entry at index 1, price 100.
    # Prices during trade: [100, 110, 90, 120]
    # MFE = 120 - 100 = 20
    # MAE = 90 - 100 = -10
    trades = evaluator._extract_trades(df)
    assert len(trades) == 1
    assert trades[0]["mfe"] == 20.0
    assert trades[0]["mae"] == -10.0


def test_session_performance_attribution():
    evaluator = RLEvaluator(env=MagicMock())
    # Mock trades at different synthetic steps (hours)
    # Asian: 22-07, London: 8-17, NY: 13-22
    # step 1 -> hour 1 (Asian)
    # step 10 -> hour 10 (London)
    # step 20 -> hour 20 (NY)
    df = pd.DataFrame({"steps": np.arange(30)})
    trades = [
        {"entry_idx": 1, "pnl": 10},  # Asian
        {"entry_idx": 10, "pnl": 20},  # London
        {"entry_idx": 20, "pnl": -5},  # NY
    ]
    perf = evaluator._calculate_session_performance(df, trades)
    assert "session_diversification" in perf
    assert perf["session_diversification"] > 0.0


def test_statistical_comparison_logic(trading_env):
    evaluator = RLEvaluator(env=trading_env)

    class ConstantAgent:
        def __init__(self, action):
            self.action = action

        def predict(self, observation):
            return self.action

    comparison = evaluator.compare(
        agents=[ConstantAgent(1)], agent_names=["Agent1"], baseline_name="Baseline"
    )

    assert "Agent1" in comparison.p_values
    assert isinstance(comparison.p_values["Agent1"], float)


def test_flip_flop_detection():
    evaluator = RLEvaluator(env=MagicMock())
    # Agent alternating Buy (1) and Sell (2) every step
    df = pd.DataFrame(
        {
            "balances": [1000] * 10,
            "actions": [1, 2, 1, 2, 1, 2, 1, 2, 1, 2],
        }
    )
    turnover = evaluator._calculate_turnover(df, [])
    # 9 potential reversal points, all are reversals
    assert turnover.flip_flop_rate == 1.0

    # No reversals
    df2 = pd.DataFrame(
        {
            "balances": [1000] * 10,
            "actions": [1, 1, 1, 1, 0, 0, 0, 2, 2, 2],
        }
    )
    turnover2 = evaluator._calculate_turnover(df2, [])
    assert turnover2.flip_flop_rate == 0.0


def test_extract_trades_reversal():
    evaluator = RLEvaluator(env=MagicMock())
    # Long reversal to Short
    df = pd.DataFrame(
        {
            "balances": [1000, 1000, 1010, 1005, 995],
            "positions": [0, 1, 1, -1, -1],
            "prices": [100, 100, 110, 105, 95],
        }
    )
    # Trade 1: Entry index 1 (price 100). Exit index 3 (price 105). Long.
    # Trade 2: Entry index 3 (price 105). Exit index 4 (price 95). Short.
    trades = evaluator._extract_trades(df)
    assert len(trades) == 2
    assert trades[0]["pnl"] == 5.0
    assert trades[0]["direction"] == 1
    # Trade 2: entry at index 3, exit at index 4.
    # pnl = balances[4] - balances[2] = 995 - 1010 = -15.0
    assert trades[1]["pnl"] == -15.0
    assert trades[1]["direction"] == -1


def test_extract_trades_initial_position():
    evaluator = RLEvaluator(env=MagicMock())
    # Position open from step 0
    df = pd.DataFrame(
        {
            "balances": [1000, 1010, 1005],
            "positions": [1, 1, 0],
            "prices": [100, 110, 105],
        }
    )
    # Trade 1: Entry 0, Exit 2.
    trades = evaluator._extract_trades(df)
    assert len(trades) == 1
    assert trades[0]["entry_idx"] == 0
    assert trades[0]["pnl"] == 5.0
