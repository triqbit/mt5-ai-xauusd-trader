"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/rl_evaluation.py
Advanced evaluation metrics for Reinforcement Learning agents.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Union, Any, Tuple

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class EvaluationMetrics(BaseModel):
    """Core performance metrics for an RL agent."""
    total_reward: float
    mean_reward: float
    std_reward: float
    sharpe_ratio: float
    max_drawdown: float
    turnover: float
    stability_score: float
    win_rate: float
    profit_factor: float
    realized_pnl: float
    unrealized_pnl: float
    transaction_costs: float

class RegimeMetrics(BaseModel):
    """Performance metrics grouped by market regime."""
    regime_name: str
    mean_reward: float
    std_reward: float
    sharpe_ratio: float
    count: int

class FullEvaluationReport(BaseModel):
    """Complete evaluation report containing metrics and regime analysis."""
    agent_name: str
    overall_metrics: EvaluationMetrics
    regime_metrics: List[RegimeMetrics]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RLEvaluator:
    """
    Evaluator for RL agents with disciplined financial metrics.
    """
    def __init__(self, env: Any, agent: Any):
        self.env = env
        self.agent = agent

    def run_evaluation(self, n_episodes: int = 5) -> FullEvaluationReport:
        """Run multiple evaluation episodes and aggregate metrics."""
        all_episode_metrics = []
        all_rewards = []
        all_actions = []
        all_balances = []

        for ep in range(n_episodes):
            obs, _ = self.env.reset()
            done = False
            truncated = False

            ep_rewards = []
            ep_actions = []
            ep_balances = []
            ep_realized_pnl = 0.0
            ep_costs = 0.0

            prev_position = 0.0

            while not (done or truncated):
                action = self.agent.predict(obs)
                obs, reward, done, truncated, info = self.env.step(action)

                ep_rewards.append(reward)
                ep_actions.append(action)
                ep_balances.append(info.get("balance", 0.0))

                # Crude cost/realized estimation if not provided by env
                # We know from gym_env.py that action 1 is Buy, 2 is Sell/Close
                # In gym_env.py, it only supports 1 position at a time.
                curr_position = info.get("position", 0.0)
                if curr_position != prev_position:
                    # Turnover/Cost calculation logic (simplistic)
                    # Real env uses commission
                    pass

                prev_position = curr_position

            all_rewards.extend(ep_rewards)
            all_actions.extend(ep_actions)
            all_balances.extend(ep_balances)

        overall_metrics = self._calculate_metrics(all_rewards, all_actions, all_balances)
        regime_metrics = self._calculate_regime_sensitivity(all_rewards)

        return FullEvaluationReport(
            agent_name=getattr(self.agent, "__class__", type(self.agent)).__name__,
            overall_metrics=overall_metrics,
            regime_metrics=regime_metrics,
            metadata={"n_episodes": n_episodes}
        )

    def _calculate_metrics(self, rewards: List[float], actions: List[int], balances: List[float]) -> EvaluationMetrics:
        """Calculate high-level financial and RL metrics."""
        rew_arr = np.array(rewards)
        act_arr = np.array(actions)
        bal_arr = np.array(balances)

        # Stability: 1 / (1 + std_reward) - simple proxy
        stability = 1.0 / (1.0 + np.std(rew_arr)) if len(rew_arr) > 0 else 0.0

        # Turnover: Frequency of action changes (non-hold actions)
        # Action 0 = Hold, 1 = Buy, 2 = Sell
        changes = np.diff(act_arr) != 0
        turnover = np.mean(changes) if len(changes) > 0 else 0.0

        # Drawdown
        if len(bal_arr) > 0:
            peak = np.maximum.accumulate(bal_arr)
            # Avoid division by zero
            drawdowns = (peak - bal_arr) / (peak + 1e-9)
            max_dd = np.max(drawdowns)
        else:
            max_dd = 0.0

        # Sharpe
        mean_rev = np.mean(rew_arr)
        std_rev = np.std(rew_arr) + 1e-9
        sharpe = (mean_rev / std_rev) * np.sqrt(252) # Annualized approx

        # Win rate (positive rewards)
        wins = rew_arr[rew_arr > 0]
        losses = rew_arr[rew_arr < 0]
        win_rate = len(wins) / len(rew_arr) if len(rew_arr) > 0 else 0.0

        # Profit factor
        profit_factor = np.sum(wins) / (abs(np.sum(losses)) + 1e-9) if len(wins) > 0 else 0.0

        return EvaluationMetrics(
            total_reward=float(np.sum(rew_arr)),
            mean_reward=float(mean_rev),
            std_reward=float(std_rev),
            sharpe_ratio=float(sharpe),
            max_drawdown=float(max_dd),
            turnover=float(turnover),
            stability_score=float(stability),
            win_rate=float(win_rate),
            profit_factor=float(profit_factor),
            realized_pnl=0.0, # Placeholder, needs env support for precise tracking
            unrealized_pnl=0.0, # Placeholder
            transaction_costs=0.0 # Placeholder
        )

    def _calculate_regime_sensitivity(self, rewards: List[float]) -> List[RegimeMetrics]:
        """Categorize performance by 'detected' regimes (High/Low Vol)."""
        if not rewards:
            return []

        # Split into 3 buckets based on reward volatility as a proxy for market regime
        # In a real scenario, this would use market features (ATR, Trend, etc.)
        rew_arr = np.array(rewards)

        # Simple split: High Vol (top 30% abs rewards), Low Vol (bottom 30%), Normal
        abs_rews = np.abs(rew_arr)
        threshold_low = np.percentile(abs_rews, 33)
        threshold_high = np.percentile(abs_rews, 66)

        regimes = []

        mask_low = abs_rews <= threshold_low
        mask_high = abs_rews >= threshold_high
        mask_normal = ~(mask_low | mask_high)

        for name, mask in [("Low Vol", mask_low), ("Normal", mask_normal), ("High Vol", mask_high)]:
            regime_rews = rew_arr[mask]
            if len(regime_rews) > 0:
                mean_r = np.mean(regime_rews)
                std_r = np.std(regime_rews) + 1e-9
                regimes.append(RegimeMetrics(
                    regime_name=name,
                    mean_reward=float(mean_r),
                    std_reward=float(std_r),
                    sharpe_ratio=float(mean_r / std_r),
                    count=len(regime_rews)
                ))

        return regimes

class RandomAgent:
    """Baseline agent that takes random actions."""
    def __init__(self, action_space: Any):
        self.action_space = action_space

    def predict(self, observation: Any) -> int:
        return self.action_space.sample()

class RuleBasedAgent:
    """Simple trend-following rule-based baseline."""
    def __init__(self):
        pass

    def predict(self, observation: np.ndarray) -> int:
        # Assuming observation ends with some features that might indicate trend
        # This is a dummy implementation; in a real scenario we'd parse the observation
        # According to TradingEnv._get_observation()
        # observation: flattened window of market data + [balance, position]
        # Let's say we just look at the last price change if possible
        # For simplicity, 0=Hold, 1=Buy, 2=Sell
        return 0 # Default to hold for now

class SupervisedAgent:
    """Wrapper for a pre-trained supervised model (e.g. LSTM/Transformer)."""
    def __init__(self, model: Any, device: str = "cpu"):
        self.model = model
        self.device = device

    def predict(self, observation: np.ndarray) -> int:
        # Placeholder for supervised inference
        # Would need to reshape observation for the model
        return 0
