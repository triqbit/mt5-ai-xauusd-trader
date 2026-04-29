"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/rl_evaluation.py
Institutional-grade reinforcement learning evaluation framework.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol

import numpy as np
from pydantic import BaseModel, Field


class EpisodeMetrics(BaseModel):
    """Metrics for a single evaluation episode."""
    episode_id: int
    total_reward: float
    pnl_reward: float
    intermediate_reward: float
    sharpe_ratio: float
    max_drawdown: float
    turnover: float
    n_steps: int
    regime_performance: Dict[str, float]

class RLPerformanceReport(BaseModel):
    """Aggregated performance report across multiple episodes."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    n_episodes: int
    mean_reward: float
    std_reward: float
    mean_sharpe: float
    mean_drawdown: float
    mean_turnover: float
    stability_score: float  # 1 - (std_reward / abs(mean_reward))
    regime_summary: Dict[str, float]
    reward_decomposition: Dict[str, float]

class AgentProtocol(Protocol):
    """Protocol for RL agents to be evaluated."""
    def predict(self, observation: np.ndarray) -> int:
        ...

class TradingEnvProtocol(Protocol):
    """Protocol for trading environments."""
    def reset(self, seed: Optional[int] = None) -> tuple[np.ndarray, dict]:
        ...
    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict]:
        ...
    @property
    def data(self) -> np.ndarray:
        ...
    @property
    def current_step(self) -> int:
        ...

class RLEvaluator:
    """
    Evaluates RL agents using institutional-grade metrics.
    """
    def __init__(self, env: TradingEnvProtocol):
        self.env = env

    def evaluate(self, agent: AgentProtocol, n_episodes: int = 10) -> RLPerformanceReport:
        episodes_metrics = []

        for i in range(n_episodes):
            metrics = self._run_episode(agent, i)
            episodes_metrics.append(metrics)

        return self._aggregate_metrics(episodes_metrics)

    def _run_episode(self, agent: AgentProtocol, episode_id: int) -> EpisodeMetrics:
        obs, info = self.env.reset()
        done = False
        rewards = []
        pnl_rewards = []
        intermediate_rewards = []
        actions = []

        # To track regime performance
        regime_rewards: Dict[str, List[float]] = {
            "TRENDING_UP": [],
            "TRENDING_DOWN": [],
            "RANGING": []
        }

        while not done:
            # Detect regime BEFORE taking action to attribute reward to the state
            regime = self._detect_regime()

            action = agent.predict(obs)
            actions.append(action)

            obs, reward, terminated, truncated, info = self.env.step(action)
            done = terminated or truncated

            rewards.append(reward)

            # Heuristic reward decomposition
            # In our TradingEnv, reward is often PnL + some unrealized
            # If info provides total_pnl, we use it.
            pnl = info.get("total_pnl", 0.0)
            # This is cumulative, so we need the delta
            last_pnl = pnl_rewards[-1] if pnl_rewards else 0.0
            pnl_delta = pnl - last_pnl

            pnl_rewards.append(pnl)
            intermediate_rewards.append(reward - pnl_delta)

            regime_rewards[regime].append(reward)

        rewards_arr = np.array(rewards)

        # Calculate Sharpe (simple version for RL evaluation)
        mean_r = np.mean(rewards_arr) if len(rewards_arr) > 0 else 0.0
        std_r = np.std(rewards_arr) if len(rewards_arr) > 0 else 1.0
        sharpe = (mean_r / (std_r + 1e-9)) * np.sqrt(252)

        # Drawdown
        cum_rewards = np.cumsum(rewards_arr)
        peak = np.maximum.accumulate(cum_rewards) if len(cum_rewards) > 0 else np.array([0.0])
        drawdown = peak - cum_rewards
        max_dd = np.max(drawdown) if len(drawdown) > 0 else 0.0

        # Turnover (action changes / n_steps)
        action_changes = np.sum(np.diff(actions) != 0)
        turnover = action_changes / len(actions) if len(actions) > 0 else 0.0

        regime_perf = {k: float(np.mean(v)) if v else 0.0 for k, v in regime_rewards.items()}

        return EpisodeMetrics(
            episode_id=episode_id,
            total_reward=float(np.sum(rewards_arr)),
            pnl_reward=float(pnl_rewards[-1] if pnl_rewards else 0.0),
            intermediate_reward=float(np.sum(intermediate_rewards)),
            sharpe_ratio=float(sharpe),
            max_drawdown=float(max_dd),
            turnover=float(turnover),
            n_steps=len(rewards),
            regime_performance=regime_perf
        )

    def _detect_regime(self) -> str:
        """Simple heuristic for regime detection using available env data."""
        try:
            data = self.env.data
            step = self.env.current_step

            if step < 20:
                return "RANGING"

            # Simple SMA based trend detection
            recent_close = data[step-20:step, 3]
            sma = np.mean(recent_close)
            current_close = data[step-1, 3]
            std = np.std(recent_close)

            if current_close > sma + 0.5 * std:
                return "TRENDING_UP"
            elif current_close < sma - 0.5 * std:
                return "TRENDING_DOWN"
            else:
                return "RANGING"
        except Exception:
            return "RANGING"

    def _aggregate_metrics(self, episodes: List[EpisodeMetrics]) -> RLPerformanceReport:
        n = len(episodes)
        if n == 0:
             return RLPerformanceReport(
                n_episodes=0, mean_reward=0, std_reward=0, mean_sharpe=0,
                mean_drawdown=0, mean_turnover=0, stability_score=0,
                regime_summary={}, reward_decomposition={}
            )

        total_rewards = [e.total_reward for e in episodes]
        sharpes = [e.sharpe_ratio for e in episodes]
        drawdowns = [e.max_drawdown for e in episodes]
        turnovers = [e.turnover for e in episodes]

        mean_reward = np.mean(total_rewards)
        std_reward = np.std(total_rewards)

        stability = 1.0 - (std_reward / (abs(mean_reward) + 1e-9))
        stability = max(0.0, min(1.0, stability))

        # Aggregate regime performance
        regime_sums: Dict[str, List[float]] = {}
        for e in episodes:
            for k, v in e.regime_performance.items():
                if k not in regime_sums:
                    regime_sums[k] = []
                regime_sums[k].append(v)

        regime_summary = {k: float(np.mean(v)) for k, v in regime_sums.items() if v}

        # Reward decomposition
        mean_pnl = np.mean([e.pnl_reward for e in episodes])
        mean_intermediate = np.mean([e.intermediate_reward for e in episodes])

        return RLPerformanceReport(
            n_episodes=n,
            mean_reward=float(mean_reward),
            std_reward=float(std_reward),
            mean_sharpe=float(np.mean(sharpes)),
            mean_drawdown=float(np.mean(drawdowns)),
            mean_turnover=float(np.mean(turnovers)),
            stability_score=float(stability),
            regime_summary=regime_summary,
            reward_decomposition={
                "pnl": float(mean_pnl),
                "intermediate": float(mean_intermediate)
            }
        )

class RandomAgent:
    """Baseline: Takes random actions."""
    def __init__(self, action_space: Any):
        self.action_space = action_space
    def predict(self, observation: np.ndarray) -> int:
        return int(self.action_space.sample())

class BuyAndHoldAgent:
    """Baseline: Always Buys (Action 1) and stays in."""
    def predict(self, observation: np.ndarray) -> int:
        return 1

class SupervisedOracleAgent:
    """
    Baseline: Uses 'future' knowledge from env data to pick best action.
    Used to establish theoretical upper bound.
    """
    def __init__(self, env: TradingEnvProtocol):
        self.env = env

    def predict(self, observation: np.ndarray) -> int:
        try:
            data = self.env.data
            step = self.env.current_step
            # Look at next close vs current close
            current_close = data[step, 3]
            next_close = data[step + 1, 3]
            if next_close > current_close:
                return 1 # Buy
            elif next_close < current_close:
                return 2 # Sell
            return 0 # Hold
        except Exception:
            return 0
