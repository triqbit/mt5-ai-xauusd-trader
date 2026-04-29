"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/stress_lab.py
Structured strategy stress testing with adversarial market conditions.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import gymnasium as gym
import numpy as np
from pydantic import BaseModel, Field

from src.environment.gym_env import TradingEnv

logger = logging.getLogger(__name__)

class StressScenario(BaseModel):
    """Configuration for an adversarial stress test scenario."""
    name: str
    description: str
    spread_multiplier: float = Field(default=1.0, ge=1.0)
    slippage_prob: float = Field(default=0.0, ge=0.0, le=1.0)
    slippage_avg_pips: float = Field(default=0.0, ge=0.0)
    missing_ticks_prob: float = Field(default=0.0, ge=0.0, le=1.0)
    execution_delay_steps: int = Field(default=0, ge=0)
    fake_breakout_prob: float = Field(default=0.0, ge=0.0, le=1.0)
    fake_breakout_sigma: float = Field(default=0.0, ge=0.0)
    price_noise_sigma: float = Field(default=0.0, ge=0.0)
    service_degradation_prob: float = Field(default=0.0, ge=0.0, le=1.0)
    regime_shift_index: Optional[int] = None
    regime_shift_vol_mult: float = Field(default=1.0, ge=1.0)

class ScenarioResult(BaseModel):
    """Result of a single stress test scenario."""
    scenario_name: str
    baseline_pnl: float
    stressed_pnl: float
    resilience_score: float  # stressed_pnl / baseline_pnl if baseline > 0
    max_drawdown_stressed: float
    win_rate_stressed: float
    failure_points: List[str] = []

class StressTestReport(BaseModel):
    """Comprehensive report aggregating multiple stress scenarios."""
    strategy_name: str
    overall_resilience_score: float
    results: List[ScenarioResult]
    fragility_indicators: List[str]
    summary: str


class AdversarialTradingEnv(TradingEnv):
    """
    Gymnasium environment that injects adversarial conditions into a TradingEnv.
    """

    def __init__(self, data: np.ndarray, scenario: StressScenario, **kwargs: Any):
        super().__init__(data, **kwargs)
        self.scenario = scenario
        self.action_queue: List[int] = []
        self._apply_data_adversity()

    def _apply_data_adversity(self):
        """Pre-process data for scenarios like missing ticks or regime shifts."""
        # Note: In a real implementation, missing ticks might involve removing rows.
        # For simplicity in this wrapper, we'll simulate missing ticks during step().
        if self.scenario.price_noise_sigma > 0:
            noise = np.random.normal(0, self.scenario.price_noise_sigma, self.data.shape)
            self.data = self.data + noise

        if self.scenario.regime_shift_index is not None:
            idx = self.scenario.regime_shift_index
            self.data[idx:, :] = self.data[idx:, :] * self.scenario.regime_shift_vol_mult

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        # 1. Service Degradation (Action dropped)
        if np.random.random() < self.scenario.service_degradation_prob:
            action = 0  # Hold instead of intended action

        # 2. Execution Delay
        if self.scenario.execution_delay_steps > 0:
            self.action_queue.append(action)
            if len(self.action_queue) <= self.scenario.execution_delay_steps:
                effective_action = 0  # Still waiting
            else:
                effective_action = self.action_queue.pop(0)
        else:
            effective_action = action

        # 3. Missing Ticks (Skip steps)
        if np.random.random() < self.scenario.missing_ticks_prob:
            # Skip this step's logic, just advance index and return current state
            self.current_step = min(self.current_step + 1, len(self.data) - 1)
            return self._get_observation(), 0.0, self.current_step >= len(self.data) - 1, False, {}

        # 4. Spread Widening & Slippage (Modified in parent logic or here)
        # We override part of the step logic to inject these.
        # Since we can't easily change the parent's private variables, we'll handle it here.

        current_price = self.data[self.current_step, 3]  # Close price

        # Inject fake breakout
        if np.random.random() < self.scenario.fake_breakout_prob:
            spike = np.random.normal(0, self.scenario.fake_breakout_sigma)
            current_price += spike

        reward = 0.0
        slippage = 0.0
        if np.random.random() < self.scenario.slippage_prob:
            # XAUUSD convention: 1.00 move = 100 pips. So 1 pip = 0.01.
            slippage = self.scenario.slippage_avg_pips * 0.01

        effective_commission = self.commission * self.scenario.spread_multiplier

        # Execute action with modified parameters
        if effective_action == 1 and self.position == 0:  # Buy
            self.position = 1.0
            self.entry_price = current_price * (1 + effective_commission) + slippage
        elif effective_action == 2 and self.position == 1:  # Sell / Close Long
            exit_price = current_price * (1 - effective_commission) - slippage
            pnl = exit_price - self.entry_price
            self.balance += pnl
            self.total_pnl += pnl
            reward = pnl / self.initial_balance * 100
            self.position = 0.0
            self.entry_price = 0.0

        if self.position == 1:
            unrealized = current_price - self.entry_price
            reward += unrealized / self.initial_balance

        self.current_step += 1
        terminated = self.balance <= 0 or self.current_step >= len(self.data) - 1
        truncated = False

        info = {
            "balance": self.balance,
            "position": self.position,
            "total_pnl": self.total_pnl,
            "scenario": self.scenario.name
        }

        return self._get_observation(), reward, terminated, truncated, info


class StressLab:
    """Coordinator for running strategy stress tests across multiple scenarios."""

    def __init__(self, data: np.ndarray, strategy: Any, initial_balance: float = 10000.0):
        self.data = data
        self.strategy = strategy
        self.initial_balance = initial_balance

    def run_stress_test(self, scenarios: List[StressScenario]) -> StressTestReport:
        """Run a suite of stress scenarios and return an aggregated report."""
        results = []
        baseline_pnl = self._run_baseline()

        for scenario in scenarios:
            result = self._run_scenario(scenario, baseline_pnl)
            results.append(result)

        overall_resilience = np.mean([r.resilience_score for r in results])
        fragility = self._identify_fragility(results)

        return StressTestReport(
            strategy_name=getattr(self.strategy, "__class__", "Unknown").__name__,
            overall_resilience_score=float(overall_resilience),
            results=results,
            fragility_indicators=fragility,
            summary=f"Strategy showed {overall_resilience:.2f} resilience across {len(scenarios)} scenarios."
        )

    def _run_baseline(self) -> float:
        """Run strategy on normal environment."""
        env = TradingEnv(self.data.copy(), initial_balance=self.initial_balance)
        metrics = self._evaluate(env)
        return metrics["total_pnl"]

    def _run_scenario(self, scenario: StressScenario, baseline_pnl: float) -> ScenarioResult:
        """Run strategy on adversarial environment."""
        env = AdversarialTradingEnv(
            self.data.copy(),
            scenario,
            initial_balance=self.initial_balance
        )
        metrics = self._evaluate(env)
        pnl = metrics["total_pnl"]

        resilience = pnl / baseline_pnl if baseline_pnl > 0 else (1.0 if pnl >= 0 else 0.0)

        failure_points = []
        if resilience < 0.3:
            failure_points.append("Severe performance degradation")
        if metrics["max_drawdown"] > 0.2 * self.initial_balance:
            failure_points.append("Excessive drawdown under stress")

        return ScenarioResult(
            scenario_name=scenario.name,
            baseline_pnl=baseline_pnl,
            stressed_pnl=pnl,
            resilience_score=float(resilience),
            max_drawdown_stressed=metrics["max_drawdown"],
            win_rate_stressed=metrics["win_rate"],
            failure_points=failure_points
        )

    def _evaluate(self, env: gym.Env) -> Dict[str, Any]:
        """Run strategy through environment and return performance metrics."""
        obs, _ = env.reset()
        done = False

        balance_history = [self.initial_balance]
        trades = []

        while not done:
            # Assumes strategy has a predict() method similar to SB3 agents
            if hasattr(self.strategy, "predict"):
                action, _ = self.strategy.predict(obs, deterministic=True)
            else:
                # Fallback to random action if strategy is not predictable
                action = env.action_space.sample()

            obs, reward, terminated, truncated, info = env.step(action)

            balance_history.append(info.get("balance", self.initial_balance))

            # Simple win rate tracking: if reward was returned for a closing trade
            if reward != 0 and info.get("position") == 0:
                trades.append(reward > 0)

            done = terminated or truncated

        # Calculate metrics
        balances = np.array(balance_history)
        peak = np.maximum.accumulate(balances)
        drawdowns = (peak - balances) / peak
        max_dd = np.max(drawdowns) if len(drawdowns) > 0 else 0.0

        win_rate = np.mean(trades) if trades else 0.0

        return {
            "total_pnl": info.get("total_pnl", 0.0),
            "max_drawdown": float(max_dd),
            "win_rate": float(win_rate)
        }

    def _identify_fragility(self, results: List[ScenarioResult]) -> List[str]:
        """Analyze results to find specific weaknesses."""
        indicators = []
        for res in results:
            if res.resilience_score < 0.5:
                indicators.append(f"Highly sensitive to {res.scenario_name}")
        return indicators
