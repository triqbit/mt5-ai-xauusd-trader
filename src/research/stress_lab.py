"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/stress_lab.py
Structured strategy stress testing and adversarial resilience framework.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import gymnasium as gym
import numpy as np
from pydantic import BaseModel, Field

from src.environment.gym_env import TradingEnv

logger = logging.getLogger(__name__)


class StressScenario(BaseModel):
    """Configuration for a specific adversarial stress test scenario."""
    name: str
    description: str

    # Execution Adversities
    spread_multiplier: float = Field(default=1.0, ge=1.0)
    slippage_bps: float = Field(default=0.0, ge=0.0)
    execution_delay_steps: int = Field(default=0, ge=0)

    # Data Adversities
    tick_drop_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    price_noise_sigma: float = Field(default=0.0, ge=0.0)

    # Market Conditions
    fake_breakout_prob: float = Field(default=0.0, ge=0.0, le=1.0)
    regime_shift: Optional[str] = None  # e.g., "volatile", "choppy"

    # Infrastructure Adversities
    service_degradation: float = Field(default=0.0, ge=0.0, le=1.0) # Prob of action failure


class StressMetrics(BaseModel):
    """Resilience metrics captured during a stress test."""
    cumulative_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    avg_slippage_paid: float
    failed_executions: int
    resilience_score: float = 0.0  # 0.0 - 1.0


class StressReport(BaseModel):
    """Comprehensive report for a strategy under stress."""
    strategy_name: str
    scenario_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    baseline_metrics: StressMetrics
    stressed_metrics: StressMetrics

    degradation_pct: float  # (Stressed - Baseline) / Baseline
    failure_points: List[str] = []
    resilience_weaknesses: List[str] = []
    is_fragile: bool = False

    summary: str


class AdversarialTradingEnv(gym.Wrapper):
    """
    Gymnasium wrapper that injects adversarial conditions into a TradingEnv.
    """
    def __init__(self, env: TradingEnv, scenario: StressScenario):
        super().__init__(env)
        self.scenario = scenario
        self.action_queue: List[Tuple[int, int]] = [] # (action, step_to_execute)
        self.total_slippage = 0.0
        self.failed_executions = 0

        # Apply data adversities if present
        if scenario.tick_drop_rate > 0 or scenario.price_noise_sigma > 0:
            self.env.unwrapped.data = self._apply_data_adversity(self.env.unwrapped.data)

    def reset(self, **kwargs) -> Tuple[np.ndarray, Dict]:
        obs, info = self.env.reset(**kwargs)
        self.action_queue = []
        self.total_slippage = 0.0
        self.failed_executions = 0
        return obs, info

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        unwrapped = self.env.unwrapped

        # 1. Service Degradation (Action Failure)
        if self.scenario.service_degradation > 0 and np.random.random() < self.scenario.service_degradation:
            logger.warning("Service degradation: action %d failed", action)
            self.failed_executions += 1
            action = 0  # Force HOLD

        # 2. Execution Delay
        if self.scenario.execution_delay_steps > 0:
            target_step = unwrapped.current_step + self.scenario.execution_delay_steps
            self.action_queue.append((action, target_step))

            current_action = 0 # Default to HOLD
            due_indices = [i for i, (a, s) in enumerate(self.action_queue) if s <= unwrapped.current_step]
            if due_indices:
                idx = due_indices[0]
                current_action, _ = self.action_queue.pop(idx)
            action = current_action

        # 3. Spread Widening & Fake Breakouts
        original_price = unwrapped.data[unwrapped.current_step, 3]

        # Simulate Fake Breakout (Price spiking then reversing)
        if self.scenario.fake_breakout_prob > 0 and action != 0 and np.random.random() < self.scenario.fake_breakout_prob:
            # Spike price against the direction to trap the trader
            spike = original_price * 0.002 * (1 if action == 1 else -1)
            unwrapped.data[unwrapped.current_step, 3] += spike
            logger.debug("Fake breakout injected at step %d", unwrapped.current_step)

        # 4. Standard execution logic through the wrapped env
        obs, reward, terminated, truncated, info = self.env.step(action)

        # 5. Apply Slippage and Spread Multiplier to the reward
        if action != 0:
            # Base spread in TradingEnv is simulated via commission
            # We add additional adversarial spread and slippage
            extra_spread_cost = (original_price * unwrapped.commission * (self.scenario.spread_multiplier - 1))
            slippage = (original_price * (self.scenario.slippage_bps / 10000.0))

            total_extra_cost = extra_spread_cost + slippage
            self.total_slippage += slippage

            # Adjust reward
            reward -= (total_extra_cost / unwrapped.initial_balance)

        return obs, reward, terminated, truncated, info

    def _apply_data_adversity(self, data: np.ndarray) -> np.ndarray:
        """Helper to pre-process data for missing ticks and noise."""
        processed = data.copy()

        # Price Noise
        if self.scenario.price_noise_sigma > 0:
            noise = np.random.normal(0, self.scenario.price_noise_sigma, (processed.shape[0], processed.shape[1]))
            processed += noise

        # Missing Ticks
        if self.scenario.tick_drop_rate > 0:
            mask = np.random.random(len(processed)) > self.scenario.tick_drop_rate
            # Ensure at least some data remains for windowing
            min_required = self.env.unwrapped.window_size + 10
            if np.sum(mask) < min_required:
                 return processed
            processed = processed[mask]

        return processed


class StressLab:
    """
    Coordinator for executing adversarial stress tests.
    """
    def __init__(self, strategy_name: str, model: Any):
        self.strategy_name = strategy_name
        self.model = model

    def run_scenario(self, env: TradingEnv, scenario: StressScenario) -> StressReport:
        """Execute a single stress scenario and return a report."""
        logger.info("Running stress scenario: %s", scenario.name)

        # 1. Run Baseline (No stress)
        # Deep copy data to avoid contamination between runs
        original_data = env.data.copy()
        baseline_metrics = self._evaluate(env)

        # 2. Run Stressed
        env.data = original_data.copy() # Reset data for stressed run
        adv_env = AdversarialTradingEnv(env, scenario)
        stressed_metrics = self._evaluate(adv_env)

        # Reset env data to original
        env.data = original_data

        # 3. Generate Report
        degradation = 0.0
        if abs(baseline_metrics.cumulative_return) > 1e-6:
            degradation = (stressed_metrics.cumulative_return - baseline_metrics.cumulative_return) / abs(baseline_metrics.cumulative_return)

        failure_points = []
        if stressed_metrics.max_drawdown > 0.25:
            failure_points.append("Excessive Drawdown (>25%)")
        if stressed_metrics.failed_executions > 10:
            failure_points.append("High Execution Failure Rate")
        if stressed_metrics.cumulative_return < 0 and baseline_metrics.cumulative_return > 0:
            failure_points.append("Strategy became unprofitable")

        is_fragile = degradation < -0.4 or stressed_metrics.max_drawdown > 0.30

        # Resilience Weaknesses detection
        weaknesses = []
        if stressed_metrics.avg_slippage_paid > 0.0005 * original_data[:, 3].mean():
            weaknesses.append("High sensitivity to slippage")
        if scenario.execution_delay_steps > 0 and degradation < -0.2:
            weaknesses.append("High sensitivity to execution latency")

        report = StressReport(
            strategy_name=self.strategy_name,
            scenario_name=scenario.name,
            baseline_metrics=baseline_metrics,
            stressed_metrics=stressed_metrics,
            degradation_pct=degradation * 100,
            failure_points=failure_points,
            resilience_weaknesses=weaknesses,
            is_fragile=is_fragile,
            summary=f"Strategy {self.strategy_name} under {scenario.name} showed {degradation*100:.1f}% degradation."
        )
        return report

    def _evaluate(self, env: gym.Env) -> StressMetrics:
        obs, _ = env.reset()
        done = False
        truncated = False

        total_reward = 0.0
        pnl_history = []
        rewards = []
        trades = 0
        wins = 0

        while not (done or truncated):
            action, _states = self.model.predict(obs, deterministic=True)
            obs, reward, done, truncated, info = env.step(action)
            total_reward += reward
            rewards.append(reward)
            pnl_history.append(info.get("total_pnl", 0.0))

            if action != 0:
                trades += 1
                if reward > 0:
                    wins += 1

        # Calculate metrics
        cum_return = pnl_history[-1] if pnl_history else 0.0

        # Max Drawdown
        peak = -np.inf
        max_dd = 0.0
        for pnl in pnl_history:
            if pnl > peak:
                peak = pnl
            dd = (peak - pnl) / (peak + 1e-8) if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        # Sharpe Ratio
        if len(rewards) > 1:
            mean_r = np.mean(rewards)
            std_r = np.std(rewards)
            sharpe = (mean_r / (std_r + 1e-8)) * np.sqrt(252 * 24 * 12) # Annualized (assuming 5min steps)
        else:
            sharpe = 0.0

        win_rate = wins / trades if trades > 0 else 0.0

        failed_executions = getattr(env, "failed_executions", 0)
        avg_slippage = getattr(env, "total_slippage", 0.0) / (trades + 1)

        # Resilience score = Weighted sum of metrics normalized
        resilience_score = max(0.0, 1.0 - (max_dd * 2.0) - (abs(min(0, cum_return)) / 1000.0))

        return StressMetrics(
            cumulative_return=cum_return,
            max_drawdown=max_dd,
            sharpe_ratio=sharpe,
            win_rate=win_rate,
            avg_slippage_paid=avg_slippage,
            failed_executions=failed_executions,
            resilience_score=resilience_score
        )
