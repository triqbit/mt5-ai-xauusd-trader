"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/rl_evaluation.py
Advanced evaluation metrics for Reinforcement Learning agents.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import numpy as np
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
        all_rewards = []
        all_actions = []
        episode_turnovers = []
        episode_drawdowns = []

        total_realized_pnl = 0.0
        total_unrealized_pnl = 0.0
        total_costs = 0.0

        closed_trades_pnl = []

        for _ in range(n_episodes):
            obs, _ = self.env.reset()
            done = False
            truncated = False

            ep_rewards = []
            ep_actions = []
            ep_balances = []

            prev_position = 0.0
            trade_unrealized_pnl = 0.0

            while not (done or truncated):
                # Handle both SB3 (action, state) and simple agents (action)
                pred = self.agent.predict(obs)
                if isinstance(pred, tuple):
                    action = pred[0]
                else:
                    action = pred

                if isinstance(action, np.ndarray):
                    action = int(action.item())

                obs, reward, done, truncated, info = self.env.step(action)

                ep_rewards.append(reward)
                ep_actions.append(action)
                ep_balances.append(info.get("balance", 0.0))

                curr_position = info.get("position", 0.0)

                # Reward Decomposition logic
                if prev_position != 0:
                    trade_unrealized_pnl += reward
                    total_unrealized_pnl += reward

                # Trade closed
                if prev_position != 0 and curr_position == 0:
                    total_realized_pnl += trade_unrealized_pnl
                    total_unrealized_pnl -= trade_unrealized_pnl
                    closed_trades_pnl.append(trade_unrealized_pnl)
                    trade_unrealized_pnl = 0.0

                # Costs tracking
                if curr_position != prev_position:
                    total_costs += 1.0

                prev_position = curr_position

            all_rewards.extend(ep_rewards)
            all_actions.extend(ep_actions)

            # Max Drawdown per episode
            if ep_balances:
                bal_arr = np.array(ep_balances)
                peak = np.maximum.accumulate(bal_arr)
                drawdowns = (peak - bal_arr) / (peak + 1e-9)
                episode_drawdowns.append(np.max(drawdowns))

            # Turnover per episode
            if len(ep_actions) > 1:
                changes = np.diff(ep_actions) != 0
                episode_turnovers.append(np.mean(changes))

        overall_metrics = self._calculate_metrics(
            all_rewards, episode_turnovers, episode_drawdowns, closed_trades_pnl
        )
        overall_metrics.realized_pnl = total_realized_pnl
        overall_metrics.unrealized_pnl = total_unrealized_pnl
        overall_metrics.transaction_costs = total_costs

        regime_metrics = self._calculate_regime_sensitivity(all_rewards)

        return FullEvaluationReport(
            agent_name=getattr(self.agent, "__class__", type(self.agent)).__name__,
            overall_metrics=overall_metrics,
            regime_metrics=regime_metrics,
            metadata={"n_episodes": n_episodes},
        )

    def _calculate_metrics(
        self,
        rewards: List[float],
        episode_turnovers: List[float],
        episode_drawdowns: List[float],
        closed_trades_pnl: List[float],
    ) -> EvaluationMetrics:
        """Calculate high-level financial and RL metrics."""
        rew_arr = np.array(rewards)

        # Stability: 1 / (1 + std_reward)
        stability = 1.0 / (1.0 + np.std(rew_arr)) if len(rew_arr) > 0 else 0.0

        # Max drawdown as the maximum observed across all episodes
        max_dd = np.max(episode_drawdowns) if episode_drawdowns else 0.0

        # Average turnover
        turnover = np.mean(episode_turnovers) if episode_turnovers else 0.0

        # Sharpe (Annualized)
        mean_rev = np.mean(rew_arr)
        std_rev = np.std(rew_arr) + 1e-9
        sharpe = (mean_rev / std_rev) * np.sqrt(252)

        # Win rate per-trade
        if closed_trades_pnl:
            wins = [p for p in closed_trades_pnl if p > 0]
            win_rate = len(wins) / len(closed_trades_pnl)

            losses = [p for p in closed_trades_pnl if p < 0]
            profit_factor = (
                sum(wins) / (abs(sum(losses)) + 1e-9) if wins else 0.0
            )
        else:
            win_rate = 0.0
            profit_factor = 0.0

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
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            transaction_costs=0.0,
        )

    def _calculate_regime_sensitivity(self, rewards: List[float]) -> List[RegimeMetrics]:
        """Categorize performance by 'detected' regimes (High/Low Vol)."""
        if not rewards:
            return []

        rew_arr = np.array(rewards)
        abs_rews = np.abs(rew_arr)
        threshold_low = np.percentile(abs_rews, 33)
        threshold_high = np.percentile(abs_rews, 66)

        regimes = []
        mask_low = abs_rews <= threshold_low
        mask_high = abs_rews >= threshold_high
        mask_normal = ~(mask_low | mask_high)

        for name, mask in [
            ("Low Vol", mask_low),
            ("Normal", mask_normal),
            ("High Vol", mask_high),
        ]:
            regime_rews = rew_arr[mask]
            if len(regime_rews) > 0:
                mean_r = np.mean(regime_rews)
                std_r = np.std(regime_rews) + 1e-9
                sharpe = (mean_r / std_r) * np.sqrt(252)
                regimes.append(
                    RegimeMetrics(
                        regime_name=name,
                        mean_reward=float(mean_r),
                        std_reward=float(std_r),
                        sharpe_ratio=float(sharpe),
                        count=len(regime_rews),
                    )
                )

        return regimes


class RandomAgent:
    """Baseline agent that takes random actions."""

    def __init__(self, action_space: Any):
        self.action_space = action_space

    def predict(self, observation: Any) -> int:
        return self.action_space.sample()


class RuleBasedAgent:
    """Simple trend-following rule-based baseline."""

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold

    def predict(self, observation: np.ndarray) -> int:
        """
        Simple trend following based on normalized market data.
        Assuming observation contains normalized price features.
        """
        # If the recent market state is significantly positive, go long.
        # If significantly negative, go short.
        if observation[-3] > self.threshold:
            return 1  # Buy
        elif observation[-3] < -self.threshold:
            return 2  # Sell
        return 0  # Hold


class SupervisedAgent:
    """Wrapper for a pre-trained supervised model."""

    def __init__(self, model: Any, device: str = "cpu"):
        self.model = model
        self.device = device

    def predict(self, observation: np.ndarray) -> int:
        # Supervised inference stub
        return 0
