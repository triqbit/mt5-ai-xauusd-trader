"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/benchmarks.py
Institutional-grade benchmarking framework for strategy evaluation.
Compares advanced models against classic algorithmic baselines.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, Tuple, Union

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from scipy import stats

logger = logging.getLogger(__name__)


class StrategyResult(BaseModel):
    """Structured performance metrics for a strategy."""
    name: str
    total_return: float
    cagr: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    volatility: float
    returns: List[float] = Field(exclude=True)


class Strategy(Protocol):
    """Protocol for all strategies to ensure consistent interface."""
    name: str

    def generate_signals(self, data: np.ndarray) -> np.ndarray:
        """
        Generate signals for the given data.
        data: (N, 5) [Open, High, Low, Close, Volume]
        Returns: np.ndarray of actions (0=Hold, 1=Buy, 2=Sell)
        """
        ...


# ── Baseline Strategies ──────────────────────────────────────────────────

class EMACrossoverStrategy:
    """Classic EMA Crossover baseline."""
    def __init__(self, fast_period: int = 12, slow_period: int = 26, name: str = "EMA_Crossover"):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.name = name

    def generate_signals(self, data: np.ndarray) -> np.ndarray:
        close = pd.Series(data[:, 3])
        ema_fast = close.ewm(span=self.fast_period, adjust=False).mean()
        ema_slow = close.ewm(span=self.slow_period, adjust=False).mean()

        signals = np.zeros(len(data))
        signals[ema_fast > ema_slow] = 1
        signals[ema_fast < ema_slow] = 2
        return signals


class MomentumStrategy:
    """Basic price momentum strategy."""
    def __init__(self, period: int = 14, threshold: float = 0.0, name: str = "Momentum"):
        self.period = period
        self.threshold = threshold
        self.name = name

    def generate_signals(self, data: np.ndarray) -> np.ndarray:
        close = pd.Series(data[:, 3])
        mom = close.diff(self.period)

        signals = np.zeros(len(data))
        signals[mom > self.threshold] = 1
        signals[mom < -self.threshold] = 2
        return signals


class VolatilityBreakoutStrategy:
    """Donchian Channel / Volatility breakout baseline."""
    def __init__(self, period: int = 20, name: str = "Vol_Breakout"):
        self.period = period
        self.name = name

    def generate_signals(self, data: np.ndarray) -> np.ndarray:
        high = pd.Series(data[:, 1])
        low = pd.Series(data[:, 2])
        close = pd.Series(data[:, 3])

        upper = high.rolling(window=self.period).max().shift(1)
        lower = low.rolling(window=self.period).min().shift(1)

        signals = np.zeros(len(data))
        signals[close > upper] = 1
        signals[close < lower] = 2
        return signals


class NaiveDirectionalStrategy:
    """Always Buy (direction=1) or Always Sell (direction=2)."""
    def __init__(self, direction: int = 1, name: str = "Buy_and_Hold"):
        self.direction = direction
        self.name = name

    def generate_signals(self, data: np.ndarray) -> np.ndarray:
        return np.full(len(data), self.direction)


class RiskFilteredBaseline:
    """
    Heuristic baseline that filters signals based on simple volatility threshold.
    Only allows trades if volatility (ATR proxy) is within a reasonable range.
    """
    def __init__(self, base_strategy: Strategy, vol_period: int = 14, max_vol_mult: float = 2.0):
        self.base_strategy = base_strategy
        self.vol_period = vol_period
        self.max_vol_mult = max_vol_mult
        self.name = f"RiskFiltered_{base_strategy.name}"

    def generate_signals(self, data: np.ndarray) -> np.ndarray:
        base_signals = self.base_strategy.generate_signals(data)

        # Calculate volatility proxy (High-Low range)
        hl_range = pd.Series(data[:, 1] - data[:, 2])
        avg_vol = hl_range.rolling(window=self.vol_period).mean()

        signals = base_signals.copy()
        # Filter out signals where current volatility is too high
        vol_mask = hl_range > (avg_vol * self.max_vol_mult)
        signals[vol_mask] = 0

        return signals


# ── Model Wrapper ────────────────────────────────────────────────────────

class ModelWrapper:
    """
    Wraps an RL Agent or Ensemble for benchmarking.
    Simulates the sliding window and state representation required by models.
    """
    def __init__(self, model: Any, window_size: int = 60, name: str = "AdvancedModel"):
        self.model = model
        self.window_size = window_size
        self.name = name

    def generate_signals(self, data: np.ndarray) -> np.ndarray:
        signals = np.zeros(len(data))

        # We need at least window_size bars
        if len(data) < self.window_size:
            return signals

        # Simplified simulation of environment observation
        for i in range(self.window_size, len(data)):
            window = data[i - self.window_size : i]
            # Normalize window (simple Z-score as in gym_env.py)
            obs_window = (window - window.mean(axis=0)) / (window.std(axis=0) + 1e-8)

            # Simplified portfolio state [balance_ratio, position]
            # In a true benchmark, we'd track this step-by-step
            portfolio_state = np.array([1.0, 0.0], dtype=np.float32)
            observation = np.concatenate([obs_window.flatten(), portfolio_state])

            # Predict
            try:
                # Handle different model interfaces
                if hasattr(self.model, "predict"):
                    action = self.model.predict(observation)
                    if isinstance(action, tuple): action = action[0]
                    signals[i] = int(action)
            except Exception as e:
                logger.debug(f"Prediction failed at step {i}: {e}")
                signals[i] = 0

        return signals


# ── Evaluator ───────────────────────────────────────────────────────────

class BenchmarkEvaluator:
    """Evaluates and compares multiple strategies."""
    def __init__(self, initial_balance: float = 10000.0, commission: float = 0.0002):
        self.initial_balance = initial_balance
        self.commission = commission

    def evaluate(self, strategy: Strategy, data: np.ndarray) -> StrategyResult:
        """Run backtest for a single strategy."""
        signals = strategy.generate_signals(data)
        close = data[:, 3]

        balance = self.initial_balance
        position = 0  # 0: None, 1: Long, 2: Short
        entry_price = 0.0
        returns = []

        wins = 0
        losses = 0
        gross_profit = 0.0
        gross_loss = 0.0

        for i in range(1, len(data)):
            current_action = int(signals[i-1])
            price = close[i]
            prev_price = close[i-1]

            step_return = 0.0

            # Handle existing positions
            if position == 1: # Long
                step_return = (price - prev_price) / prev_price
                # Exit signal (Hold or Sell)
                if current_action in [0, 2]:
                    trade_pnl = (price * (1 - self.commission)) - entry_price
                    balance += trade_pnl
                    if trade_pnl > 0:
                        wins += 1
                        gross_profit += trade_pnl
                    else:
                        losses += 1
                        gross_loss += abs(trade_pnl)
                    position = 0

            elif position == 2: # Short
                step_return = (prev_price - price) / prev_price
                # Exit signal (Hold or Buy)
                if current_action in [0, 1]:
                    trade_pnl = entry_price - (price * (1 + self.commission))
                    balance += trade_pnl
                    if trade_pnl > 0:
                        wins += 1
                        gross_profit += trade_pnl
                    else:
                        losses += 1
                        gross_loss += abs(trade_pnl)
                    position = 0

            # Open new positions if currently flat
            if position == 0:
                if current_action == 1:
                    position = 1
                    entry_price = price * (1 + self.commission)
                elif current_action == 2:
                    position = 2
                    entry_price = price * (1 - self.commission)

            returns.append(step_return)

        rets_arr = np.array(returns)
        total_ret = (balance - self.initial_balance) / self.initial_balance

        # Calculate Metrics
        vol = float(rets_arr.std() * np.sqrt(252)) if len(rets_arr) > 0 else 0.0
        avg_ret = float(rets_arr.mean()) if len(rets_arr) > 0 else 0.0
        sharpe = (avg_ret / (rets_arr.std() + 1e-9)) * np.sqrt(252) if len(rets_arr) > 0 else 0.0

        downside_rets = rets_arr[rets_arr < 0]
        sortino = (avg_ret / (downside_rets.std() + 1e-9)) * np.sqrt(252) if len(downside_rets) > 0 else 0.0

        cum_rets = np.cumsum(returns)
        running_max = np.maximum.accumulate(cum_rets)
        drawdown = running_max - cum_rets
        max_dd = float(np.max(drawdown)) if len(drawdown) > 0 else 0.0

        total_trades = wins + losses
        win_rate = wins / total_trades if total_trades > 0 else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else gross_profit

        return StrategyResult(
            name=strategy.name,
            total_return=total_ret,
            cagr=total_ret,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=total_trades,
            volatility=vol,
            returns=returns
        )

    def compare(self, strategies: List[Strategy], data: np.ndarray) -> pd.DataFrame:
        """Compare multiple strategies and return a summary DataFrame."""
        results = []
        for strat in strategies:
            res = self.evaluate(strat, data)
            # Use model_dump() for pydantic v2
            results.append(res.model_dump())

        df = pd.DataFrame(results)
        return df

    @staticmethod
    def calculate_p_value(res1: StrategyResult, res2: StrategyResult) -> float:
        """Calculate p-value using t-test to see if res1 is statistically different from res2."""
        if not res1.returns or not res2.returns:
            return 1.0
        t_stat, p_val = stats.ttest_ind(res1.returns, res2.returns, equal_var=False)
        return float(p_val)
