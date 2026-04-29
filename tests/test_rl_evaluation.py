import numpy as np

from src.research.rl_evaluation import BuyAndHoldAgent, RLEvaluator, SupervisedOracleAgent


class MockEnv:
    def __init__(self, data):
        self._data = data
        self.current_step = 0
        self.action_space = type('obj', (object,), {'sample': lambda: 1})()

    @property
    def data(self):
        return self._data

    def reset(self, seed=None):
        self.current_step = 0
        return np.zeros((10,)), {}

    def step(self, action):
        self.current_step += 1
        done = self.current_step >= len(self._data) - 1
        reward = 1.0 if action == 1 else -1.0
        info = {"total_pnl": float(self.current_step)}
        return np.zeros((10,)), reward, done, False, info

def test_evaluator_metrics():
    # 50 steps of data
    data = np.zeros((100, 5))
    data[:, 3] = np.linspace(100, 200, 100) # Uptrend

    env = MockEnv(data)
    evaluator = RLEvaluator(env)

    # Agent that always buys
    class AlwaysBuyAgent:
        def predict(self, obs): return 1

    report = evaluator.evaluate(AlwaysBuyAgent(), n_episodes=2)

    assert report.n_episodes == 2
    assert report.mean_reward > 0
    assert "pnl" in report.reward_decomposition
    assert "TRENDING_UP" in report.regime_summary

def test_baselines():
    data = np.zeros((100, 5))
    data[:, 3] = np.linspace(100, 200, 100)
    env = MockEnv(data)

    bh_agent = BuyAndHoldAgent()
    assert bh_agent.predict(None) == 1

    oracle = SupervisedOracleAgent(env)
    env.current_step = 10
    # Next close > current close in our linspace
    assert oracle.predict(None) == 1

def test_stability_score():
    from src.research.rl_evaluation import EpisodeMetrics
    evaluator = RLEvaluator(None)

    # Mocking aggregate_metrics
    episodes = [
        EpisodeMetrics(
            episode_id=0, total_reward=100.0, pnl_reward=100.0, intermediate_reward=0.0,
            sharpe_ratio=1.0, max_drawdown=5.0, turnover=0.1, n_steps=10, regime_performance={}
        ),
        EpisodeMetrics(
            episode_id=1, total_reward=110.0, pnl_reward=110.0, intermediate_reward=0.0,
            sharpe_ratio=1.1, max_drawdown=4.0, turnover=0.1, n_steps=10, regime_performance={}
        )
    ]

    report = evaluator._aggregate_metrics(episodes)
    assert 0.0 <= report.stability_score <= 1.0
    assert report.mean_reward == 105.0
