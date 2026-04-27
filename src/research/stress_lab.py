"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/stress_lab.py

Structured strategy stress testing and adversarial resilience analysis.
This module provides tools to replay adverse market conditions and evaluate
strategy performance under degradation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Tuple, Union

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from src.environment.gym_env import TradingEnv

logger = logging.getLogger(__name__)

class StressType(str, Enum):
    SPREAD_WIDENING = "spread_widening"
    SLIPPAGE_SPIKE = "slippage_spike"
    MISSING_TICKS = "missing_ticks"
    DELAYED_FILLS = "delayed_fills"
    CHOPPY_FAKE_BREAKOUT = "choppy_fake_breakout"
    REGIME_TRANSITION = "regime_transition"
    DEGRADED_SERVICE = "degraded_service"

class StressScenario(BaseModel):
    """Configuration for a specific stress test scenario."""
    name: str
    stress_type: StressType
    intensity: float = Field(default=1.0, description="Multiplier for stress effect")
    params: Dict[str, Union[float, int, str]] = Field(default_factory=dict)

class StressTestResult(BaseModel):
    """Outcome of a single stress scenario."""
    scenario_name: str
    baseline_pnl: float
    stressed_pnl: float
    degradation_pct: float
    resilience_score: float  # 0.0 to 1.0
    failure_points: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StressReport(BaseModel):
    """Aggregated stress lab report."""
    strategy_id: str
    results: List[StressTestResult]
    overall_resilience_score: float
    weaknesses: List[str]
    recommendations: List[str]

class AdversarialTradingEnv(TradingEnv):
    """
    An extension of the standard TradingEnv that injects adversarial execution conditions.
    """
    def __init__(self, *args, **kwargs):
        self.slippage_mean = kwargs.pop("slippage_mean", 0.0)
        self.slippage_std = kwargs.pop("slippage_std", 0.0)
        self.latency_steps = kwargs.pop("latency_steps", 0)
        self.pending_actions: List[Tuple[int, int]] = [] # (action, fill_at_step)
        super().__init__(*args, **kwargs)

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        # Handle Latency
        effective_action = 0
        if self.latency_steps > 0:
            if action != 0: # If trying to Buy/Sell
                self.pending_actions.append((action, self.current_step + self.latency_steps))

            # Check if any pending actions should be executed now
            remaining_pending = []
            for act, fill_step in self.pending_actions:
                if self.current_step >= fill_step:
                    # In this env, usually only one action per step makes sense
                    # We take the oldest pending action that is ready
                    if effective_action == 0:
                        effective_action = act
                    else:
                        # If multiple are ready (unlikely), keep others for next steps
                        remaining_pending.append((act, fill_step))
                else:
                    remaining_pending.append((act, fill_step))
            self.pending_actions = remaining_pending
        else:
            effective_action = action

        # Apply Slippage to the execution if an action is being taken
        original_commission = self.commission
        if effective_action != 0:
            noise = max(0, np.random.normal(self.slippage_mean, self.slippage_std))
            self.commission += noise # Simulating slippage as extra cost

        obs, reward, term, trunc, info = super().step(effective_action)

        # Restore commission
        self.commission = original_commission
        return obs, reward, term, trunc, info

class AdversarialEngine:
    """
    Engine to apply adversarial transformations to market data.
    """

    @staticmethod
    def simulate_missing_ticks(data: np.ndarray, drop_rate: float = 0.05) -> np.ndarray:
        """
        Randomly drop rows to simulate feed instability.
        """
        if len(data) == 0:
            return data
        df = pd.DataFrame(data)
        mask = np.random.rand(len(df)) > drop_rate
        # Ensure we don't drop everything if data is small
        if mask.sum() == 0:
            return data
        return df[mask].values

    @staticmethod
    def inject_choppy_regime(data: np.ndarray, intensity: float = 1.0) -> np.ndarray:
        """
        Inject high-frequency noise and fake breakouts into the price action.
        """
        noisy_data = data.copy()
        # Add noise to High and Low to simulate choppiness
        noise = np.random.normal(0, np.std(data[:, 3]) * 0.1 * intensity, size=(data.shape[0],))
        noisy_data[:, 1] += np.abs(noise) # High higher
        noisy_data[:, 2] -= np.abs(noise) # Low lower
        return noisy_data

    @staticmethod
    def inject_regime_transition(data: np.ndarray, intensity: float = 1.0) -> np.ndarray:
        """
        Simulate a sudden regime shift (e.g., from trending to mean-reverting or a V-reversal).
        We do this by flipping the direction of the last 20% of the data.
        """
        modified_data = data.copy()
        transition_point = int(len(data) * 0.8)
        if transition_point < len(data):
            for i in range(transition_point, len(data)):
                diff = data[i, 3] - data[i-1, 3] if i > 0 else 0
                # Flip the price movement
                modified_data[i, 3] = modified_data[i-1, 3] - diff * intensity
                # Adjust OHL to match new Close
                modified_data[i, 0] = modified_data[i-1, 3]
                modified_data[i, 1] = max(modified_data[i, 0], modified_data[i, 3]) + abs(diff) * 0.5
                modified_data[i, 2] = min(modified_data[i, 0], modified_data[i, 3]) - abs(diff) * 0.5
        return modified_data

class StressLab:
    """
    Main orchestrator for running stress tests.
    """

    def __init__(self, model_predict_fn):
        """
        model_predict_fn: function that takes (obs) and returns action
        """
        self.predict_fn = model_predict_fn
        self.scenarios: List[StressScenario] = []

    def add_scenario(self, scenario: StressScenario):
        self.scenarios.append(scenario)

    def run_all(self, baseline_data: np.ndarray) -> StressReport:
        results = []
        # Run baseline
        baseline_pnl, _ = self._run_session(baseline_data)
        logger.info("Baseline PnL: %.4f", baseline_pnl)

        for scenario in self.scenarios:
            logger.info("Running scenario: %s", scenario.name)
            res = self._run_scenario(baseline_data, scenario, baseline_pnl)
            results.append(res)

        overall_resilience = np.mean([r.resilience_score for r in results]) if results else 1.0
        weaknesses = [r.scenario_name for r in results if r.resilience_score < 0.8]

        return StressReport(
            strategy_id="Strategy_V1",
            results=results,
            overall_resilience_score=overall_resilience,
            weaknesses=weaknesses,
            recommendations=self._generate_recommendations(weaknesses)
        )

    def _run_scenario(self, data: np.ndarray, scenario: StressScenario, baseline_pnl: float) -> StressTestResult:
        engine = AdversarialEngine()
        stressed_data = data.copy()
        env_kwargs = {}

        if scenario.stress_type == StressType.MISSING_TICKS:
            stressed_data = engine.simulate_missing_ticks(data, drop_rate=0.05 * scenario.intensity)
        elif scenario.stress_type == StressType.CHOPPY_FAKE_BREAKOUT:
            stressed_data = engine.inject_choppy_regime(data, intensity=scenario.intensity)
        elif scenario.stress_type == StressType.REGIME_TRANSITION:
            stressed_data = engine.inject_regime_transition(data, intensity=scenario.intensity)
        elif scenario.stress_type == StressType.SLIPPAGE_SPIKE:
            env_kwargs["slippage_mean"] = 0.0005 * scenario.intensity
            env_kwargs["slippage_std"] = 0.0002 * scenario.intensity
        elif scenario.stress_type == StressType.DELAYED_FILLS:
            env_kwargs["latency_steps"] = int(1 * scenario.intensity)
        elif scenario.stress_type == StressType.SPREAD_WIDENING:
            env_kwargs["commission"] = 0.0002 * (1 + scenario.intensity)
        elif scenario.stress_type == StressType.DEGRADED_SERVICE:
            stressed_data = engine.simulate_missing_ticks(data, drop_rate=0.1 * scenario.intensity)
            env_kwargs["latency_steps"] = int(2 * scenario.intensity)
            env_kwargs["slippage_mean"] = 0.0003 * scenario.intensity

        stressed_pnl, failure_points = self._run_session(stressed_data, **env_kwargs)

        degradation = 0.0
        if abs(baseline_pnl) > 1e-6:
            degradation = (baseline_pnl - stressed_pnl) / abs(baseline_pnl)
        elif stressed_pnl < 0:
            degradation = 1.0 # Significant degradation from neutral baseline

        resilience = max(0.0, min(1.0, 1.0 - degradation))

        return StressTestResult(
            scenario_name=scenario.name,
            baseline_pnl=baseline_pnl,
            stressed_pnl=stressed_pnl,
            degradation_pct=degradation * 100,
            resilience_score=resilience,
            failure_points=failure_points
        )

    def _run_session(self, data: np.ndarray, **env_kwargs) -> Tuple[float, List[str]]:
        """Runs a single backtest session. Returns (total_pnl, failure_points)."""
        env = AdversarialTradingEnv(data, **env_kwargs)
        obs, _ = env.reset()
        done = False
        total_pnl = 0.0
        failure_points = []
        step_count = 0

        while not done:
            action = self.predict_fn(obs)
            obs, reward, terminated, truncated, info = env.step(action)

            # Identify failure points: significant negative rewards or high drawdown
            if reward < -0.5: # 0.5% loss in one step is significant
                failure_points.append(f"Step {step_count}: Significant negative reward {reward:.4f}")

            done = terminated or truncated
            step_count += 1

        total_pnl = info.get("total_pnl", 0.0)
        return total_pnl, failure_points[:10] # Limit to top 10 failure points

    def _generate_recommendations(self, weaknesses: List[str]) -> List[str]:
        recs = []
        mapping = {
            StressType.SPREAD_WIDENING: "Increase minimum confidence threshold for entries.",
            StressType.SLIPPAGE_SPIKE: "Use limit orders or tighter slippage tolerance.",
            StressType.MISSING_TICKS: "Implement data sanity checks and interpolation.",
            StressType.DELAYED_FILLS: "Optimize execution pipeline and reduce feature calculation latency.",
            StressType.CHOPPY_FAKE_BREAKOUT: "Add a volatility filter or ADX-based trend confirmation.",
            StressType.REGIME_TRANSITION: "Implement a market regime detector to adjust strategy parameters dynamically.",
            StressType.DEGRADED_SERVICE: "Enable circuit breakers and fail-to-safe modes for high-latency conditions."
        }
        for w in weaknesses:
            for st in StressType:
                if st.value in w.lower():
                    recs.append(mapping.get(st, "Review strategy logic for this condition."))
        return list(set(recs))

if __name__ == "__main__":
    # Quick sanity check
    data = np.random.randn(1000, 5) # Dummy OHLCV
    lab = StressLab(lambda obs: np.random.randint(0, 3))
    lab.add_scenario(StressScenario(name="High Slippage", stress_type=StressType.SLIPPAGE_SPIKE, intensity=2.0))
    lab.add_scenario(StressScenario(name="Wide Spread", stress_type=StressType.SPREAD_WIDENING, intensity=3.0))
