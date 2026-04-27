"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/benchmarks.py
Comparative benchmarking framework for trading strategies.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Protocol

import numpy as np
import pandas as pd
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class BenchmarkReport(BaseModel):
    """Structured report for strategy performance."""

    strategy_name: str
    cumulative_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int


class Strategy(Protocol):
    """Protocol for trading strategies to ensure a consistent evaluation interface."""

    name: str

    def predict(self, obs: np.ndarray, info: Optional[Dict[str, Any]] = None) -> int:
        """
        Generate a trading action.
        0 = Hold, 1 = Buy, 2 = Sell (Close)
        """
        ...


class BaseBaseline:
    """Base class for simple baseline strategies."""

    def __init__(self, name: str, window_size: int = 60):
        self.name = name
        self.window_size = window_size

    def _unflatten_obs(self, obs: np.ndarray) -> np.ndarray:
        """Extract market data window from the flattened observation."""
        obs_size = len(obs)
        # observation_space shape is (window_size * n_features + 2,)
        n_features = (obs_size - 2) // self.window_size
        window_data = obs[: self.window_size * n_features]
        return window_data.reshape((self.window_size, n_features))


class EMACrossoverBaseline(BaseBaseline):
    """Fast vs Slow Exponential Moving Average crossover."""

    def __init__(self, fast_period: int = 10, slow_period: int = 30, **kwargs):
        super().__init__(name="EMA_Crossover", **kwargs)
        self.fast_period = fast_period
        self.slow_period = slow_period

    def predict(self, obs: np.ndarray, info: Optional[Dict[str, Any]] = None) -> int:
        data = self._unflatten_obs(obs)
        close = data[:, 3]

        df = pd.DataFrame(close, columns=["close"])
        ema_fast = df["close"].ewm(span=self.fast_period).mean().iloc[-1]
        ema_slow = df["close"].ewm(span=self.slow_period).mean().iloc[-1]

        current_position = obs[-1]

        if ema_fast > ema_slow:
            return 1 if current_position == 0 else 0
        else:
            return 2 if current_position == 1 else 0


class MomentumBaseline(BaseBaseline):
    """Simple price momentum strategy."""

    def __init__(self, period: int = 14, threshold: float = 0.0, **kwargs):
        super().__init__(name="Momentum", **kwargs)
        self.period = period
        self.threshold = threshold

    def predict(self, obs: np.ndarray, info: Optional[Dict[str, Any]] = None) -> int:
        data = self._unflatten_obs(obs)
        close = data[:, 3]
        momentum = close[-1] - close[-self.period]

        current_position = obs[-1]

        if momentum > self.threshold:
            return 1 if current_position == 0 else 0
        elif momentum < -self.threshold:
            return 2 if current_position == 1 else 0
        return 0


class VolatilityBreakoutBaseline(BaseBaseline):
    """Bollinger-style volatility breakout strategy."""

    def __init__(self, period: int = 20, k: float = 2.0, **kwargs):
        super().__init__(name="Volatility_Breakout", **kwargs)
        self.period = period
        self.k = k

    def predict(self, obs: np.ndarray, info: Optional[Dict[str, Any]] = None) -> int:
        data = self._unflatten_obs(obs)
        close = data[:, 3]

        rolling_mean = np.mean(close[-self.period :])
        rolling_std = np.std(close[-self.period :])

        upper_band = rolling_mean + self.k * rolling_std
        lower_band = rolling_mean - self.k * rolling_std

        current_position = obs[-1]

        if close[-1] > upper_band:
            return 1 if current_position == 0 else 0
        elif close[-1] < lower_band:
            return 2 if current_position == 1 else 0
        return 0


class NaiveDirectionalBaseline(BaseBaseline):
    """Follows the direction of the last candle."""

    def __init__(self, **kwargs):
        super().__init__(name="Naive_Directional", **kwargs)

    def predict(self, obs: np.ndarray, info: Optional[Dict[str, Any]] = None) -> int:
        data = self._unflatten_obs(obs)
        last_close = data[-1, 3]
        last_open = data[-1, 0]

        current_position = obs[-1]

        if last_close > last_open:
            return 1 if current_position == 0 else 0
        else:
            return 2 if current_position == 1 else 0


class RiskFilteredBaseline:
    """Wraps a strategy and applies additional heuristic risk filters."""

    def __init__(self, base_strategy: Strategy, min_volatility: float = 0.001):
        self.base_strategy = base_strategy
        self.min_volatility = min_volatility
        self.name = f"RiskFiltered_{getattr(base_strategy, 'name', 'Strategy')}"

    def predict(self, obs: np.ndarray, info: Optional[Dict[str, Any]] = None) -> int:
        # Example filter: avoid trading if recent volatility is too low
        # observation_space shape is (window_size * n_features + 2,)
        window_size = getattr(self.base_strategy, "window_size", 60)
        n_features = (len(obs) - 2) // window_size
        window_data = obs[: window_size * n_features].reshape((window_size, n_features))

        close = window_data[:, 3]
        vol = np.std(close)

        if vol < self.min_volatility:
            return 0

        return self.base_strategy.predict(obs, info)


class BenchmarkEvaluator:
    """Orchestrates evaluation of multiple strategies on a given environment."""

    def __init__(self, env):
        self.env = env

    def evaluate(self, strategy: Strategy, n_episodes: int = 5) -> BenchmarkReport:
        """Run multiple episodes and aggregate results."""
        all_episode_returns = []
        all_step_returns = []
        episode_max_drawdowns = []
        total_wins = 0
        total_trades = 0

        for _ in range(n_episodes):
            obs, info = self.env.reset()
            done = False
            truncated = False
            initial_balance = getattr(self.env, "initial_balance", 10000.0)

            # For per-episode drawdown
            current_episode_balances = [initial_balance]

            while not (done or truncated):
                action = strategy.predict(obs, info)
                action = max(0, min(2, int(action)))

                next_obs, reward, done, truncated, info = self.env.step(action)
                current_balance = info.get("balance", initial_balance)

                # step reward in TradingEnv.step is pnl / initial_balance * 100
                # we want decimal fractional returns for Sharpe
                step_return = reward / 100.0 if action == 2 else reward
                all_step_returns.append(step_return)

                current_episode_balances.append(current_balance)

                # Count trades and wins. action=2 is close in TradingEnv.step
                if action == 2:
                    total_trades += 1
                    if reward > 0:
                        total_wins += 1

                obs = next_obs

            final_balance = info.get("balance", initial_balance)
            final_return = (final_balance - initial_balance) / initial_balance
            all_episode_returns.append(final_return)

            # Calculate Max Drawdown for this episode
            ep_balance_arr = np.array(current_episode_balances)
            peak = np.maximum.accumulate(ep_balance_arr)
            safe_peak = np.where(peak == 0, 1e-9, peak)
            drawdown = (peak - ep_balance_arr) / safe_peak
            episode_max_drawdowns.append(np.max(drawdown))

        cumulative_return = np.mean(all_episode_returns)
        win_rate = total_wins / total_trades if total_trades > 0 else 0.0

        # Sharpe Ratio (annualised from step-level returns)
        # We assume each step is a bar (e.g. 1 hour). 252 days * 24 hours = 6048 steps
        # This is a heuristic, in production it should match timeframe.
        step_returns_arr = np.array(all_step_returns)
        mean_step_ret = np.mean(step_returns_arr)
        std_step_ret = np.std(step_returns_arr) + 1e-9
        # Assuming 252 trading days and average steps per day (e.g. 24 if H1)
        # Defaulting to 252 for simplicity in this baseline tool
        sharpe = (mean_step_ret / std_step_ret) * np.sqrt(252)

        max_dd = np.mean(episode_max_drawdowns)

        return BenchmarkReport(
            strategy_name=strategy.name,
            cumulative_return=float(cumulative_return),
            sharpe_ratio=float(sharpe),
            max_drawdown=float(max_dd),
            win_rate=float(win_rate),
            total_trades=int(total_trades),
        )


def generate_comparison_table(reports: List[BenchmarkReport]) -> pd.DataFrame:
    """Convert a list of reports into a pandas DataFrame for easy comparison."""
    data = [report.model_dump() for report in reports]
    df = pd.DataFrame(data)
    cols = [
        "strategy_name",
        "cumulative_return",
        "sharpe_ratio",
        "max_drawdown",
        "win_rate",
        "total_trades",
    ]
    return df[cols]
