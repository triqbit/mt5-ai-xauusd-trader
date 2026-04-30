"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/rl_evaluation.py
Reinforcement Learning Evaluation Framework for institutional-grade agent analysis.
Provides metrics for stability, turnover, drawdown, and regime sensitivity.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Protocol, Union

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ── Metrics Data Models ──────────────────────────────────────────────────

class DrawdownMetrics(BaseModel):
    """Metrics related to drawdown and risk behavior."""
    max_drawdown: float = Field(..., description="Maximum peak-to-trough decline (fraction)")
    max_drawdown_duration: int = Field(..., description="Longest drawdown period in steps")
    average_drawdown: float = Field(..., description="Average drawdown across all periods")
    recovery_factor: float = Field(..., description="Total profit / Max drawdown")


class TurnoverMetrics(BaseModel):
    """Metrics related to trading activity and costs."""
    total_trades: int = Field(..., description="Total number of completed trades")
    action_frequency: float = Field(..., description="Percentage of steps with non-HOLD actions")
    turnover_rate: float = Field(..., description="Average position change per step")
    total_cost_paid: float = Field(..., description="Cumulative transaction costs and fees")


class StabilityMetrics(BaseModel):
    """Metrics related to reward consistency and robustness."""
    sharpe_ratio: float = Field(..., description="Risk-adjusted return (annualized)")
    sortino_ratio: float = Field(..., description="Downside risk-adjusted return")
    win_rate: float = Field(..., description="Percentage of profitable trades")
    reward_volatility: float = Field(..., description="Standard deviation of step-wise rewards")
    profit_factor: float = Field(..., description="Gross profit / Gross loss")


class RegimeSensitivity(BaseModel):
    """Performance metrics broken down by market regime."""
    trending_sharpe: float = Field(..., description="Sharpe ratio during high-volatility/trending periods")
    ranging_sharpe: float = Field(..., description="Sharpe ratio during low-volatility/ranging periods")
    volatility_correlation: float = Field(..., description="Correlation between market volatility and agent performance")


class EvaluationReport(BaseModel):
    """Comprehensive evaluation report for a trading agent."""
    agent_name: str
    total_steps: int
    final_balance: float
    total_return: float
    drawdown: DrawdownMetrics
    turnover: TurnoverMetrics
    stability: StabilityMetrics
    regime_sensitivity: Optional[RegimeSensitivity] = None
    reward_decomposition: Dict[str, float] = Field(
        default_factory=dict,
        description="Breakdown of reward sources (e.g., pnl, commissions, penalties)"
    )


# ── Agent Protocols and Base Classes ────────────────────────────────────────

class TradingAgent(Protocol):
    """Protocol for any agent that can generate actions from observations."""

    def predict(self, observation: np.ndarray) -> Union[int, np.ndarray]:
        """Generate action(s) for the given observation."""
        ...


class MomentumBaseline:
    """Rule-based baseline using price momentum."""

    def __init__(self, lookback: int = 5):
        self.lookback = lookback

    def predict(self, observation: np.ndarray) -> int:
        """
        Predict action based on simple momentum.
        Assumes observation is flattened and close price is at index 3 of each bar.
        """
        # We assume 5 features per bar.
        # Observation is a window of N bars.
        # To be robust, we look at the last few elements.
        if len(observation) < 10:
            return 0

        # Heuristic: if last bar close > prev bar close, buy.
        # This is a proxy for the evaluator structure.
        current_close = observation[-3]
        prev_close = observation[-8]

        if current_close > prev_close:
            return 1  # Buy
        elif current_close < prev_close:
            return 2  # Sell
        return 0  # Hold


class SupervisedBaselineWrapper:
    """Wrapper for supervised models (like LSTM-Attention) to fit the TradingAgent protocol."""

    def __init__(self, model):
        self.model = model

    def predict(self, observation: np.ndarray) -> int:
        """Predict action using the wrapped supervised model."""
        if hasattr(self.model, "predict"):
            # EnsembleModel returns (direction, confidence, per_algo)
            # direction: +1 buy, -1 sell, 0 hold
            # Environment expects: 0=hold, 1=buy, 2=sell
            direction, _, _ = self.model.predict(observation)
            mapping = {1: 1, -1: 2, 0: 0}
            return mapping.get(direction, 0)
        return 0


# ── Core Evaluator ────────────────────────────────────────────────────────

class RLEvaluator:
    """
    Main evaluation engine for RL agents.
    Handles episode execution, metric gathering, and report generation.
    """

    def __init__(self, env, n_eval_episodes: int = 5, periods_per_year: int = 72576):
        """
        initialise with environment and annualization constant.
        Default periods_per_year = 252 days * 24 hours * 12 (5-min bars) = 72576.
        """
        self.env = env
        self.n_eval_episodes = n_eval_episodes
        self.periods_per_year = periods_per_year

    def run_evaluation(self, agent: TradingAgent, agent_name: str) -> EvaluationReport:
        """
        Execute evaluation episodes and compute detailed metrics.
        """
        all_episode_rewards = []
        all_balances = []
        all_actions = []
        all_pnl = []
        all_infos = []
        total_steps = 0

        for _ in range(self.n_eval_episodes):
            obs, _ = self.env.reset()
            done = False
            truncated = False
            ep_rewards = []
            ep_actions = []
            ep_infos = []

            while not (done or truncated):
                action = agent.predict(obs)
                if isinstance(action, np.ndarray):
                    action = int(action.item())

                obs, reward, done, truncated, info = self.env.step(action)

                ep_rewards.append(reward)
                ep_actions.append(action)
                ep_infos.append(info)
                total_steps += 1

            all_episode_rewards.append(ep_rewards)
            all_balances.append(info.get("balance", self.env.initial_balance))
            all_actions.append(ep_actions)
            all_pnl.append(info.get("total_pnl", 0.0))
            all_infos.append(ep_infos)

        # Flatten data for analysis
        flat_rewards = [r for ep in all_episode_rewards for r in ep]
        flat_actions = [a for ep in all_actions for a in ep]
        flat_infos = [i for ep in all_infos for i in ep]

        # 1. Calculate stability
        stability = self._calculate_stability(flat_rewards)

        # 2. Calculate drawdown
        drawdown = self._calculate_drawdown(all_balances)

        # 3. Calculate turnover and costs
        turnover = self._calculate_turnover(flat_actions, flat_infos, total_steps)

        # 4. Calculate regime sensitivity (volatility-based)
        regime = self._calculate_regime_sensitivity(flat_rewards)

        # 5. Reward decomposition
        decomp = self._decompose_rewards(flat_rewards, flat_infos)

        return EvaluationReport(
            agent_name=agent_name,
            total_steps=total_steps,
            final_balance=np.mean(all_balances),
            total_return=(np.mean(all_balances) - self.env.initial_balance) / self.env.initial_balance,
            drawdown=drawdown,
            turnover=turnover,
            stability=stability,
            regime_sensitivity=regime,
            reward_decomposition=decomp
        )

    def _calculate_stability(self, rewards: List[float]) -> StabilityMetrics:
        """Compute Sharpe, Sortino, Win Rate, and Profit Factor."""
        rets = np.array(rewards)
        if len(rets) < 2:
            return StabilityMetrics(
                sharpe_ratio=0.0, sortino_ratio=0.0, win_rate=0.0,
                reward_volatility=0.0, profit_factor=0.0
            )

        avg_ret = np.mean(rets)
        std_ret = np.std(rets) + 1e-9
        sharpe = (avg_ret / std_ret) * np.sqrt(self.periods_per_year)

        downside_rets = rets[rets < 0]
        sortino = (avg_ret / (np.std(downside_rets) + 1e-9)) * np.sqrt(self.periods_per_year) if len(downside_rets) > 0 else 0.0

        win_rate = len(rets[rets > 0]) / len(rets) if len(rets) > 0 else 0.0

        gross_profit = np.sum(rets[rets > 0])
        gross_loss = abs(np.sum(rets[rets < 0]))
        profit_factor = gross_profit / (gross_loss + 1e-9)

        return StabilityMetrics(
            sharpe_ratio=float(sharpe),
            sortino_ratio=float(sortino),
            win_rate=float(win_rate),
            reward_volatility=float(std_ret),
            profit_factor=float(profit_factor)
        )

    def _calculate_drawdown(self, balances: List[float]) -> DrawdownMetrics:
        """Compute MDD, Duration, and Recovery Factor."""
        bals = np.array(balances)
        peak = np.maximum.accumulate(bals)
        drawdowns = (peak - bals) / (peak + 1e-9)

        max_dd = np.max(drawdowns)

        # Duration calculation
        is_in_dd = drawdowns > 1e-6
        dd_durations = []
        current_dur = 0
        for in_dd in is_in_dd:
            if in_dd:
                current_dur += 1
            else:
                if current_dur > 0:
                    dd_durations.append(current_dur)
                current_dur = 0
        if current_dur > 0:
            dd_durations.append(current_dur)

        max_dd_dur = max(dd_durations) if dd_durations else 0

        total_profit = bals[-1] - bals[0]
        recovery_factor = total_profit / (max_dd * bals[0] + 1e-9)

        return DrawdownMetrics(
            max_drawdown=float(max_dd),
            max_drawdown_duration=int(max_dd_dur),
            average_drawdown=float(np.mean(drawdowns)),
            recovery_factor=float(recovery_factor)
        )

    def _calculate_turnover(self, actions: List[int], infos: List[dict], total_steps: int) -> TurnoverMetrics:
        """Compute trade counts, frequency, and turnover rate."""
        acts = np.array(actions)
        non_hold = acts[acts != 0]

        action_freq = len(non_hold) / total_steps if total_steps > 0 else 0.0

        trades = 0
        for i in range(1, len(acts)):
            if acts[i] != acts[i-1] and acts[i-1] != 0:
                trades += 1

        turnover_rate = np.sum(np.diff(acts) != 0) / total_steps if total_steps > 0 else 0.0

        # Try to extract commissions from info, else estimate based on env config
        total_cost = 0.0
        comm_found = False
        for info in infos:
            if "commission" in info:
                total_cost += info["commission"]
                comm_found = True

        if not comm_found and hasattr(self.env, "commission"):
            # Estimate: each trade incurs entry commission
            total_cost = trades * self.env.commission * self.env.initial_balance

        return TurnoverMetrics(
            total_trades=trades,
            action_frequency=float(action_freq),
            turnover_rate=float(turnover_rate),
            total_cost_paid=float(total_cost)
        )

    def _calculate_regime_sensitivity(self, rewards: List[float]) -> RegimeSensitivity:
        """Volatility-based regime sensitivity analysis."""
        rets = np.array(rewards)
        if len(rets) < 20:
            return RegimeSensitivity(trending_sharpe=0.0, ranging_sharpe=0.0, volatility_correlation=0.0)

        # Estimate rolling volatility as a regime proxy
        vol = pd.Series(rets).rolling(20).std().fillna(0).values
        median_vol = np.median(vol)

        high_vol_idx = vol > median_vol
        low_vol_idx = vol <= median_vol

        def calc_sharpe(r):
            if len(r) < 2:
                return 0.0
            return (np.mean(r) / (np.std(r) + 1e-9)) * np.sqrt(self.periods_per_year)

        trending_s = calc_sharpe(rets[high_vol_idx])
        ranging_s = calc_sharpe(rets[low_vol_idx])

        # Correlation between reward and local volatility
        corr = np.corrcoef(rets, vol)[0, 1] if np.std(vol) > 0 else 0.0

        return RegimeSensitivity(
            trending_sharpe=float(trending_s),
            ranging_sharpe=float(ranging_s),
            volatility_correlation=float(corr) if not np.isnan(corr) else 0.0
        )

    def _decompose_rewards(self, rewards: List[float], infos: List[dict]) -> Dict[str, float]:
        """Attempt to split reward into PnL and other components found in info."""
        decomp = {"total": sum(rewards)}

        # If env info contains specific reward components, aggregate them
        keys = ["pnl_reward", "cost_penalty", "hold_penalty", "consistency_bonus"]
        for key in keys:
            val = sum(i.get(key, 0.0) for i in infos)
            if val != 0:
                decomp[key] = val

        if len(decomp) == 1: # Only total
            decomp["unattributed"] = decomp["total"]

        return decomp
