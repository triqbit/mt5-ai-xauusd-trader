"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/rl_evaluation.py
Institutional-grade RL agent evaluation framework.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Protocol

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from src.models.regime_detector import MarketRegime, RegimeDetector

logger = logging.getLogger(__name__)


class RLModel(Protocol):
    """Protocol for RL agents to ensure consistent evaluation."""

    def predict(self, observation: np.ndarray) -> int: ...


class StabilityMetrics(BaseModel):
    """Metrics assessing the consistency and risk-adjusted returns."""

    sharpe_ratio: float = Field(..., description="Annualized Sharpe Ratio")
    sortino_ratio: float = Field(..., description="Annualized Sortino Ratio")
    volatility: float = Field(..., description="Annualized volatility")
    stability_score: float = Field(..., description="Metric for consistency of returns")


class TurnoverMetrics(BaseModel):
    """Metrics assessing trading activity and execution costs."""

    trade_frequency: float = Field(..., description="Number of trades per 1000 steps")
    avg_hold_time: float = Field(..., description="Average steps per trade")
    total_trades: int
    turnover_ratio: float = Field(..., description="Total traded volume relative to balance")


class DrawdownMetrics(BaseModel):
    """Metrics assessing downside risk and recovery."""

    max_drawdown: float = Field(..., description="Maximum peak-to-trough decline")
    max_drawdown_duration: int = Field(..., description="Maximum steps spent in drawdown")
    avg_drawdown: float = Field(..., description="Average drawdown depth")


class RegimePerformance(BaseModel):
    """Performance metrics segmented by market regime."""

    regime: MarketRegime
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    profit_factor: float


class RewardDecomposition(BaseModel):
    """Breakdown of returns into gross profit and costs."""

    gross_pnl: float
    net_pnl: float
    total_commissions: float
    commission_drag: float = Field(
        ..., description="Percentage impact of commissions on gross returns"
    )


class RLReport(BaseModel):
    """Final aggregate evaluation report for an RL agent."""

    agent_name: str
    total_steps: int
    stability: StabilityMetrics
    turnover: TurnoverMetrics
    drawdown: DrawdownMetrics
    regime_sensitivity: List[RegimePerformance]
    reward_decomposition: RewardDecomposition
    overall_win_rate: float


class RLEvaluator:
    """
    Evaluator for RL agents with institutional metrics.
    Analyzes performance beyond simple reward, focusing on stability,
    turnover, and regime sensitivity.
    """

    def __init__(
        self,
        env: Any,
        regime_detector: Optional[RegimeDetector] = None,
        annualization_factor: int = 252,
    ):
        self.env = env
        self.regime_detector = regime_detector or RegimeDetector()
        self.annualization_factor = annualization_factor

    def evaluate(self, agent: RLModel, agent_name: str = "RL_Agent") -> RLReport:
        """Run a full evaluation of the agent and generate a typed report."""
        obs, _ = self.env.reset()
        done = False

        history = {
            "steps": [],
            "actions": [],
            "rewards": [],
            "balances": [],
            "positions": [],
            "regimes": [],
            "commissions": [],
        }

        step_idx = 0
        while not done:
            action = agent.predict(obs)
            next_obs, reward, terminated, truncated, info = self.env.step(action)

            # Detect market regime
            current_regime = MarketRegime.UNKNOWN
            if hasattr(self.env, "data") and hasattr(self.env, "current_step"):
                # Handle both raw numpy and potentially wrapped envs
                data = self.env.data
                current_step = self.env.current_step

                if current_step >= 100:
                    df_slice = pd.DataFrame(
                        data[current_step - 100 : current_step],
                        columns=["open", "high", "low", "close", "tick_volume"],
                    )
                    current_regime = self.regime_detector.detect(df_slice).label

            history["steps"].append(step_idx)
            history["actions"].append(action)
            history["rewards"].append(reward)
            history["balances"].append(info["balance"])
            history["positions"].append(info["position"])
            history["regimes"].append(current_regime)
            history["commissions"].append(info.get("cumulative_commissions", 0.0))

            obs = next_obs
            done = terminated or truncated
            step_idx += 1

        df_history = pd.DataFrame(history)

        return self._generate_report(agent_name, df_history)

    def _generate_report(self, agent_name: str, df: pd.DataFrame) -> RLReport:
        """Calculate all metrics and return an RLReport."""
        stability = self._calculate_stability(df)
        turnover = self._calculate_turnover(df)
        drawdown = self._calculate_drawdown(df)
        regime_sensitivity = self._calculate_regime_sensitivity(df)
        reward_decomp = self._calculate_reward_decomposition(df)

        trades = self._extract_trades(df)
        win_rate = len([t for t in trades if t > 0]) / len(trades) if trades else 0.0

        return RLReport(
            agent_name=agent_name,
            total_steps=len(df),
            stability=stability,
            turnover=turnover,
            drawdown=drawdown,
            regime_sensitivity=regime_sensitivity,
            reward_decomposition=reward_decomp,
            overall_win_rate=win_rate,
        )

    def _extract_trades(self, df: pd.DataFrame) -> List[float]:
        """Extract individual trade PNls from history."""
        trade_pnls = []
        balances = df["balances"].values
        positions = df["positions"].values

        for i in range(1, len(df)):
            if positions[i - 1] != 0 and positions[i] == 0:
                pnl = balances[i] - balances[i - 1]
                trade_pnls.append(pnl)
        return trade_pnls

    def _calculate_stability(self, df: pd.DataFrame) -> StabilityMetrics:
        """Assess the consistency and risk-adjusted returns."""
        returns = df["balances"].pct_change().dropna()
        if len(returns) < 2:
            return StabilityMetrics(
                sharpe_ratio=0.0, sortino_ratio=0.0, volatility=0.0, stability_score=0.0
            )

        mean_ret = returns.mean()
        std_ret = returns.std()

        sharpe = (mean_ret / std_ret * np.sqrt(self.annualization_factor)) if std_ret > 0 else 0.0

        downside_ret = returns[returns < 0]
        downside_std = downside_ret.std()
        sortino = (
            (mean_ret / downside_std * np.sqrt(self.annualization_factor))
            if downside_std > 0
            else 0.0
        )

        vol = std_ret * np.sqrt(self.annualization_factor)

        # Stability score: consistency of equity curve (R-squared of linear fit)
        x = np.arange(len(df))
        y = df["balances"].values
        slope, intercept = np.polyfit(x, y, 1)
        line = slope * x + intercept
        r_squared = 1 - (np.sum((y - line) ** 2) / np.sum((y - y.mean()) ** 2))

        return StabilityMetrics(
            sharpe_ratio=float(sharpe),
            sortino_ratio=float(sortino),
            volatility=float(vol),
            stability_score=float(r_squared),
        )

    def _calculate_turnover(self, df: pd.DataFrame) -> TurnoverMetrics:
        """Assess trading activity and execution costs."""
        positions = df["positions"].values
        trades = 0
        total_hold_time = 0
        current_hold_time = 0

        for i in range(1, len(positions)):
            if positions[i] != 0:
                current_hold_time += 1
                if positions[i - 1] == 0:
                    trades += 1
            elif positions[i - 1] != 0:
                total_hold_time += current_hold_time
                current_hold_time = 0

        avg_hold_time = total_hold_time / trades if trades > 0 else 0.0
        trade_freq = (trades / len(df)) * 1000

        # Turnover ratio: rough estimate of traded volume relative to initial balance
        # In this env, each trade is 1.0 unit.
        turnover_ratio = (trades * 1.0) / (df["balances"].iloc[0]) if len(df) > 0 else 0.0

        return TurnoverMetrics(
            trade_frequency=float(trade_freq),
            avg_hold_time=float(avg_hold_time),
            total_trades=trades,
            turnover_ratio=float(turnover_ratio),
        )

    def _calculate_drawdown(self, df: pd.DataFrame) -> DrawdownMetrics:
        """Assess downside risk and recovery."""
        balances = df["balances"].values
        peak = np.maximum.accumulate(balances)
        drawdowns = (peak - balances) / peak

        max_dd = np.max(drawdowns)
        avg_dd = np.mean(drawdowns[drawdowns > 0]) if np.any(drawdowns > 0) else 0.0

        # Max drawdown duration
        is_in_dd = drawdowns > 0
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

        return DrawdownMetrics(
            max_drawdown=float(max_dd),
            max_drawdown_duration=int(max_dd_dur),
            avg_drawdown=float(avg_dd),
        )

    def _calculate_regime_sensitivity(self, df: pd.DataFrame) -> List[RegimePerformance]:
        """Performance metrics segmented by market regime."""
        regime_stats = []
        unique_regimes = df["regimes"].unique()

        for regime in unique_regimes:
            if regime == MarketRegime.UNKNOWN:
                continue

            regime_df = df[df["regimes"] == regime]
            if len(regime_df) < 10:  # Ignore regimes with too little data
                continue

            returns = regime_df["balances"].pct_change().dropna()
            sharpe = (
                (returns.mean() / returns.std() * np.sqrt(self.annualization_factor))
                if len(returns) > 1 and returns.std() > 0
                else 0.0
            )

            # Extract trades within this regime
            # Simplified: look for balance changes where regime is current
            regime_pnls = []
            balances = df["balances"].values
            positions = df["positions"].values
            regimes = df["regimes"].values

            for i in range(1, len(df)):
                if positions[i - 1] != 0 and positions[i] == 0 and regimes[i - 1] == regime:
                    pnl = balances[i] - balances[i - 1]
                    regime_pnls.append(pnl)

            win_rate = (
                len([p for p in regime_pnls if p > 0]) / len(regime_pnls) if regime_pnls else 0.0
            )

            # Profit factor: sum(profits) / abs(sum(losses))
            profits = sum([p for p in regime_pnls if p > 0])
            losses = abs(sum([p for p in regime_pnls if p < 0]))
            profit_factor = (
                profits / losses if losses > 0 else (float("inf") if profits > 0 else 1.0)
            )

            regime_stats.append(
                RegimePerformance(
                    regime=regime,
                    sharpe_ratio=float(sharpe),
                    win_rate=float(win_rate),
                    total_trades=len(regime_pnls),
                    profit_factor=float(profit_factor),
                )
            )

        return regime_stats

    def _calculate_reward_decomposition(self, df: pd.DataFrame) -> RewardDecomposition:
        """Breakdown of returns into gross profit and costs."""
        total_commissions = df["commissions"].iloc[-1] if len(df) > 0 else 0.0
        final_pnl = df["balances"].iloc[-1] - df["balances"].iloc[0] if len(df) > 0 else 0.0

        net_pnl = final_pnl
        gross_pnl = net_pnl + total_commissions

        comm_drag = (total_commissions / gross_pnl * 100) if gross_pnl > 0 else 0.0

        return RewardDecomposition(
            gross_pnl=float(gross_pnl),
            net_pnl=float(net_pnl),
            total_commissions=float(total_commissions),
            commission_drag=float(comm_drag),
        )


class MomentumBaseline:
    """Rule-based momentum baseline for RL comparison."""

    def __init__(self, window: int = 14):
        self.window = window

    def predict(self, observation: np.ndarray) -> int:
        """
        Simple momentum: if current price > price N steps ago, buy.
        Note: This expects the observation to contain historical prices.
        In TradingEnv, observations are normalized windows.
        We'll use a simplified version: if the latest normalized value is positive, buy.
        """
        # Observation format from TradingEnv: [window_normalized, balance, position]
        # Close price is at index 3 in each step's features.
        # But here they are flattened.
        # Let's assume a simplified logic for the baseline that can work on the obs.
        # For a true baseline, it might be better to have access to raw data,
        # but for this wrapper we'll look at the last feature of the window.

        # Roughly, the last element before balance/position is the last feature of the last step.
        last_val = observation[-3]
        if last_val > 0.5:
            return 1  # Buy
        elif last_val < -0.5:
            return 2  # Sell
        return 0  # Hold


class SupervisedBaseline:
    """Wrapper for supervised models to compare against RL agents."""

    def __init__(self, model: Any):
        self.model = model

    def predict(self, observation: np.ndarray) -> int:
        # Assuming supervised model returns 0, 1, 2
        # We might need to reshape observation for the model
        obs_reshaped = observation.reshape(1, -1)
        action = self.model.predict(obs_reshaped)
        if isinstance(action, np.ndarray):
            return int(action[0])
        return int(action)
