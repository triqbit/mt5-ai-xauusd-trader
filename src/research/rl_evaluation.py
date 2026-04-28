"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/rl_evaluation.py
Reinforcement Learning evaluation framework for disciplined performance analysis.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable

import numpy as np
import pandas as pd
from pydantic import BaseModel

logger = logging.getLogger(__name__)

@runtime_checkable
class TradingEnvProtocol(Protocol):
    """Protocol defining the expected interface for the trading environment."""
    data: np.ndarray
    current_step: int
    initial_balance: float
    balance: float
    entry_price: float
    def reset(self, seed: Optional[int] = None) -> Tuple[np.ndarray, Dict]: ...
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]: ...
    @property
    def action_space(self) -> Any: ...

class RLStrategy(Protocol):
    """Protocol for RL agents to ensure compatibility."""
    def predict(self, obs: np.ndarray, deterministic: bool = True) -> Any:
        ...

class EpisodeMetrics(BaseModel):
    """Metrics for a single evaluation episode."""
    total_reward: float
    cumulative_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    turnover: float
    stability_score: float  # inverse of reward variance
    realized_pnl: float
    unrealized_pnl: float

class RegimeMetrics(BaseModel):
    """Metrics segmented by market regime."""
    regime_name: str
    avg_reward: float
    win_rate: float
    count: int

class RLPerformanceReport(BaseModel):
    """Typed report for RL agent evaluation."""
    agent_name: str
    episodes: List[EpisodeMetrics]
    mean_metrics: EpisodeMetrics
    regime_analysis: List[RegimeMetrics]
    comparison_baselines: Dict[str, float]  # baseline_name -> mean_reward

class RLEvaluator:
    """
    Institutional-grade RL evaluation framework.
    Evaluates agents beyond simple rewards, focusing on stability, risk, and regime robustness.
    """

    def __init__(self, env: Any, agent: Any):
        self.env = env
        self.agent = agent
        # Assuming index 3 is Close price based on common OHLCV format
        self.price_idx = 3

    def evaluate(self, n_episodes: int = 5) -> RLPerformanceReport:
        """
        Run comprehensive evaluation over multiple episodes.
        """
        episode_results = []
        regime_data: List[Dict[str, Any]] = []

        for i in range(n_episodes):
            logger.info(f"Evaluating episode {i+1}/{n_episodes}")
            metrics, history = self._run_episode()
            episode_results.append(metrics)
            regime_data.extend(history)

        # Aggregate metrics
        mean_metrics = self._aggregate_metrics(episode_results)

        # Regime sensitivity
        regime_analysis = self._analyze_regimes(regime_data)

        # Baselines
        baselines = self._evaluate_baselines()

        return RLPerformanceReport(
            agent_name=self.agent.__class__.__name__ if hasattr(self.agent, "__class__") else "Agent",
            episodes=episode_results,
            mean_metrics=mean_metrics,
            regime_analysis=regime_analysis,
            comparison_baselines=baselines
        )

    def _run_episode(self) -> Tuple[EpisodeMetrics, List[Dict[str, Any]]]:
        """Run a single episode and collect detailed metrics and history."""
        obs, info = self.env.reset()
        done = False
        rewards = []
        actions = []
        history = []

        initial_balance = getattr(self.env, "initial_balance", 10000.0)
        balance_history = [getattr(self.env, "balance", initial_balance)]

        realized_pnl = 0.0

        while not done:
            if hasattr(self.agent, "predict"):
                prediction = self.agent.predict(obs, deterministic=True)
                action = int(prediction[0]) if isinstance(prediction, tuple) else int(prediction)
            else:
                action = 0

            # Capture regime info before step if available
            regime = self._detect_simple_regime()

            obs, reward, terminated, truncated, info = self.env.step(action)
            done = terminated or truncated

            rewards.append(reward)
            actions.append(action)
            current_balance = info.get("balance", getattr(self.env, "balance", initial_balance))
            balance_history.append(current_balance)

            if "total_pnl" in info:
                realized_pnl = info["total_pnl"]

            history.append({
                "reward": reward,
                "regime": regime,
                "win": reward > 0
            })

        rewards_arr = np.array(rewards)
        actions_arr = np.array(actions)
        balance_arr = np.array(balance_history)

        stability = 1.0 / (np.std(rewards_arr) + 1e-6)

        turnover = 0.0
        if len(actions_arr) > 1:
            changes = np.sum(actions_arr[1:] != actions_arr[:-1])
            turnover = float(changes) / len(actions_arr)

        peak = np.maximum.accumulate(balance_arr)
        safe_peak = np.where(peak == 0, 1e-9, peak)
        drawdown = (peak - balance_arr) / safe_peak
        max_dd = np.max(drawdown) if len(drawdown) > 0 else 0.0

        std_reward = np.std(rewards_arr)
        sharpe = (np.mean(rewards_arr) / (std_reward + 1e-9)) * np.sqrt(252) if std_reward > 0 else 0.0

        metrics = EpisodeMetrics(
            total_reward=float(np.sum(rewards_arr)),
            cumulative_return=float((balance_arr[-1] - balance_arr[0]) / balance_arr[0]) if balance_arr[0] != 0 else 0.0,
            max_drawdown=float(max_dd),
            sharpe_ratio=float(sharpe),
            win_rate=float(np.mean(rewards_arr > 0)) if len(rewards_arr) > 0 else 0.0,
            turnover=float(turnover),
            stability_score=float(stability),
            realized_pnl=float(realized_pnl),
            unrealized_pnl=0.0 # simplified
        )
        return metrics, history

    def _detect_simple_regime(self) -> str:
        """Heuristic regime detection based on available env data."""
        try:
            data = getattr(self.env, "data", None)
            step = getattr(self.env, "current_step", 0)
            if data is not None and step > 20:
                recent = data[step-20:step, self.price_idx]
                sma = np.mean(recent)
                current = data[step, self.price_idx]
                vol = np.std(recent)

                regime = "Ranging"
                if current > sma + vol:
                    regime = "Trending Up"
                elif current < sma - vol:
                    regime = "Trending Down"
                return regime
        except Exception:
            pass
        return "Unknown"

    def _analyze_regimes(self, history: List[Dict[str, Any]]) -> List[RegimeMetrics]:
        """Aggregate performance by detected regime."""
        if not history:
            return []

        df = pd.DataFrame(history)
        if "regime" not in df.columns:
            return []

        analysis = []
        for regime, group in df.groupby("regime"):
            analysis.append(RegimeMetrics(
                regime_name=str(regime),
                avg_reward=float(group["reward"].mean()),
                win_rate=float(group["win"].mean()),
                count=len(group)
            ))
        return analysis

    def _evaluate_baselines(self) -> Dict[str, float]:
        """Evaluate comparison baselines."""
        return {
            "BuyAndHold": self._run_baseline_bh(),
            "Random": self._run_baseline_random(),
            "SupervisedSim": self._run_baseline_supervised()
        }

    def _run_baseline_bh(self) -> float:
        self.env.reset()
        _, reward, term, trunc, _ = self.env.step(1) # Buy
        total = reward
        while not (term or trunc):
            _, reward, term, trunc, _ = self.env.step(0) # Hold
            total += reward
        return float(total)

    def _run_baseline_random(self) -> float:
        self.env.reset()
        total = 0.0
        done = False
        while not done:
            _, reward, term, trunc, _ = self.env.step(self.env.action_space.sample())
            total += reward
            done = term or trunc
        return float(total)

    def _run_baseline_supervised(self) -> float:
        """Simulate a supervised model following perfect trend."""
        self.env.reset()
        total = 0.0
        done = False
        while not done:
            # Oracle-like trend following
            try:
                data = self.env.data
                step = self.env.current_step
                action = 1 if data[step, self.price_idx] > data[step-1, self.price_idx] else 2
            except Exception:
                action = 0
            _, reward, term, trunc, _ = self.env.step(action)
            total += reward
            done = term or trunc
        return float(total)

    def _aggregate_metrics(self, episodes: List[EpisodeMetrics]) -> EpisodeMetrics:
        if not episodes:
            return EpisodeMetrics(
                total_reward=0, cumulative_return=0, max_drawdown=0,
                sharpe_ratio=0, win_rate=0, turnover=0,
                stability_score=0, realized_pnl=0, unrealized_pnl=0
            )
        return EpisodeMetrics(
            total_reward=float(np.mean([e.total_reward for e in episodes])),
            cumulative_return=float(np.mean([e.cumulative_return for e in episodes])),
            max_drawdown=float(np.mean([e.max_drawdown for e in episodes])),
            sharpe_ratio=float(np.mean([e.sharpe_ratio for e in episodes])),
            win_rate=float(np.mean([e.win_rate for e in episodes])),
            turnover=float(np.mean([e.turnover for e in episodes])),
            stability_score=float(np.mean([e.stability_score for e in episodes])),
            realized_pnl=float(np.mean([e.realized_pnl for e in episodes])),
            unrealized_pnl=0.0
        )
