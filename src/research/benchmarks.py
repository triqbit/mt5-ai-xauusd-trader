"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/benchmarks.py
Benchmarking framework to compare advanced models against baseline strategies.
"""

from __future__ import annotations

from typing import Any, Dict, List, Protocol

import numpy as np
import pandas as pd
from scipy import stats

from src.core.constants import SignalDirection


class BenchmarkStrategy(Protocol):
    """Protocol for all strategies and baselines to ensure consistent evaluation."""

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Generate signals for a given dataset.
        Args:
            df: DataFrame containing OHLCV data and technical indicators.
        Returns:
            np.ndarray: Array of signals (1: Buy, -1: Sell, 0: Hold).
        """
        ...

    @property
    def name(self) -> str:
        """Return the name of the strategy."""
        ...


class EMACrossoverStrategy:
    """Simple EMA Crossover baseline."""

    def __init__(self, fast_window: int = 9, slow_window: int = 21):
        self.fast_window = fast_window
        self.slow_window = slow_window

    @property
    def name(self) -> str:
        return f"EMA_Crossover_{self.fast_window}_{self.slow_window}"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        fast_ema = df["close"].ewm(span=self.fast_window, adjust=False).mean()
        slow_ema = df["close"].ewm(span=self.slow_window, adjust=False).mean()

        signals = np.zeros(len(df))
        signals[fast_ema > slow_ema] = 1
        signals[fast_ema < slow_ema] = -1
        return signals


class MomentumStrategy:
    """Momentum-based (ROC) baseline."""

    def __init__(self, window: int = 14):
        self.window = window

    @property
    def name(self) -> str:
        return f"Momentum_ROC_{self.window}"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        roc = df["close"].pct_change(periods=self.window)
        signals = np.zeros(len(df))
        signals[roc > 0] = 1
        signals[roc < 0] = -1
        return signals


class VolatilityBreakoutStrategy:
    """Bollinger Band Breakout baseline."""

    def __init__(self, window: int = 20, num_std: float = 2.0):
        self.window = window
        self.num_std = num_std

    @property
    def name(self) -> str:
        return f"Volatility_Breakout_{self.window}_{self.num_std}"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        rolling_mean = df["close"].rolling(window=self.window).mean()
        rolling_std = df["close"].rolling(window=self.window).std()
        upper_band = rolling_mean + (rolling_std * self.num_std)
        lower_band = rolling_mean - (rolling_std * self.num_std)

        signals = np.zeros(len(df))
        signals[df["close"] > upper_band] = 1
        signals[df["close"] < lower_band] = -1
        return signals


class NaiveDirectionalStrategy:
    """Naive 'Follow the Leader' (last candle direction) strategy."""

    @property
    def name(self) -> str:
        return "Naive_Directional"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        diff = df["close"].diff()
        signals = np.zeros(len(df))
        signals[diff > 0] = 1
        signals[diff < 0] = -1
        return signals


class RiskFilteredBaseline:
    """EMA Crossover strategy with a simple volatility filter."""

    def __init__(
        self, fast_window: int = 9, slow_window: int = 21, vol_threshold_pct: float = 0.02
    ):
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.vol_threshold_pct = vol_threshold_pct

    @property
    def name(self) -> str:
        return f"Risk_Filtered_EMA_{self.vol_threshold_pct}"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        fast_ema = df["close"].ewm(span=self.fast_window, adjust=False).mean()
        slow_ema = df["close"].ewm(span=self.slow_window, adjust=False).mean()
        volatility = df["close"].rolling(window=20).std() / df["close"]

        signals = np.zeros(len(df))
        # Only trade if volatility is below threshold
        mask = volatility < self.vol_threshold_pct
        signals[mask & (fast_ema > slow_ema)] = 1
        signals[mask & (fast_ema < slow_ema)] = -1
        return signals


class MeanReversionStrategy:
    """RSI-based Mean Reversion baseline."""

    def __init__(self, window: int = 14, overbought: int = 70, oversold: int = 30):
        self.window = window
        self.overbought = overbought
        self.oversold = oversold

    @property
    def name(self) -> str:
        return f"Mean_Reversion_RSI_{self.window}"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.window).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        signals = np.zeros(len(df))
        signals[rsi < self.oversold] = 1
        signals[rsi > self.overbought] = -1
        return signals


class BenchmarkEvaluator:
    """Evaluates multiple strategies and generates comparative reports."""

    def __init__(
        self, df: pd.DataFrame, initial_balance: float = 10000.0, commission: float = 0.0002
    ):
        self.df = df
        self.initial_balance = initial_balance
        self.commission = commission
        self.results: Dict[str, Any] = {}

    def evaluate_all(self, strategies: List[BenchmarkStrategy]) -> pd.DataFrame:
        """Run evaluation for all provided strategies."""
        summary = {}
        for strategy in strategies:
            signals = strategy.predict(self.df)
            metrics = self._calculate_metrics(signals, strategy.name)
            self.results[strategy.name] = metrics
            summary[strategy.name] = metrics

        return pd.DataFrame(summary).T

    def _calculate_metrics(self, signals: np.ndarray, name: str) -> Dict[str, Any]:
        """Backtest signals and calculate performance metrics using equity curve."""
        close = self.df["close"].values
        n = len(signals)
        equity = np.ones(n) * self.initial_balance
        daily_returns = np.zeros(n)
        trade_pnls = []

        position = 0
        entry_equity = self.initial_balance

        for i in range(1, n):
            target_pos = signals[i - 1]
            prev_price = close[i - 1]
            current_price = close[i]
            current_equity = equity[i - 1]

            # Handle transitions (Closures / Reversals / Entries)
            if target_pos != position:
                # If closing an existing position
                if position != 0:
                    current_equity *= 1 - self.commission
                    trade_pnls.append(current_equity - entry_equity)

                # If opening a new position
                if target_pos != 0:
                    current_equity *= 1 - self.commission
                    entry_equity = current_equity

                position = target_pos

            # Update equity based on market movement
            if position == 1:
                change = (current_price - prev_price) / prev_price
                current_equity *= 1 + change
            elif position == -1:
                change = (prev_price - current_price) / prev_price
                current_equity *= 1 + change

            equity[i] = current_equity
            daily_returns[i] = (
                (equity[i] - equity[i - 1]) / equity[i - 1] if equity[i - 1] != 0 else 0
            )

        # Force close any remaining position at the last price
        if position != 0:
            equity[-1] *= 1 - self.commission
            trade_pnls.append(equity[-1] - entry_equity)

        # Final aggregate metrics
        total_return = (equity[-1] - self.initial_balance) / self.initial_balance

        sharpe = 0.0
        sortino = 0.0
        if np.std(daily_returns) > 0:
            # Assuming 252 trading days for annualization
            avg_return = np.mean(daily_returns)
            sharpe = avg_return / np.std(daily_returns) * np.sqrt(252)

            downside_returns = daily_returns[daily_returns < 0]
            downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 0
            if downside_std > 0:
                sortino = avg_return / downside_std * np.sqrt(252)

        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / peak
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0

        win_rate = 0.0
        profit_factor = 0.0
        expectancy = 0.0
        if len(trade_pnls) > 0:
            wins = [p for p in trade_pnls if p > 0]
            losses = [p for p in trade_pnls if p < 0]
            win_rate = len(wins) / len(trade_pnls)

            gains_sum = sum(wins)
            losses_sum = abs(sum(losses))
            profit_factor = gains_sum / losses_sum if losses_sum > 0 else float("inf")

            avg_win = np.mean(wins) if wins else 0
            avg_loss = abs(np.mean(losses)) if losses else 0
            loss_rate = len(losses) / len(trade_pnls)
            expectancy = (avg_win * win_rate) - (avg_loss * loss_rate)

        calmar = total_return / max_drawdown if max_drawdown > 0 else 0.0

        # Store daily returns for statistical testing
        self.results[name + "_returns"] = daily_returns

        return {
            "Total Return": total_return,
            "Sharpe Ratio": sharpe,
            "Sortino Ratio": sortino,
            "Calmar Ratio": calmar,
            "Max Drawdown": max_drawdown,
            "Win Rate": win_rate,
            "Profit Factor": profit_factor,
            "Expectancy": expectancy,
            "Num Trades": len(trade_pnls),
        }

    def compare_to_baseline(self, strategy_name: str, baseline_name: str) -> Dict[str, Any]:
        """Perform statistical comparison between a strategy and a baseline."""
        if strategy_name not in self.results or baseline_name not in self.results:
            return {"error": "Strategy or baseline not found in results."}

        s_metrics = self.results[strategy_name]
        b_metrics = self.results[baseline_name]

        s_returns = self.results.get(strategy_name + "_returns", np.array([]))
        b_returns = self.results.get(baseline_name + "_returns", np.array([]))

        # Welch's t-test on return distributions
        t_stat, p_value = stats.ttest_ind(s_returns, b_returns, equal_var=False)

        # Simple relative performance
        outperformance = s_metrics["Total Return"] - b_metrics["Total Return"]
        sharpe_diff = s_metrics["Sharpe Ratio"] - b_metrics["Sharpe Ratio"]

        return {
            "Outperformance": outperformance,
            "Sharpe Improvement": sharpe_diff,
            "Relative Return": outperformance / (abs(b_metrics["Total Return"]) + 1e-9),
            "T-Statistic": float(t_stat),
            "P-Value": float(p_value),
            "Significant": bool(p_value < 0.05) if not np.isnan(p_value) else False,
        }

    def to_report_section(self, baseline_name: str) -> Any:
        """
        Convert results into a BenchmarkSection for the ResearchReporter.
        Requires src.research.reporting models to be available.
        """
        from src.research.reporting import BenchmarkComparison, BenchmarkSection

        comparisons = []
        for name, metrics in self.results.items():
            if name.endswith("_returns") or name == baseline_name:
                continue

            comp = self.compare_to_baseline(name, baseline_name)
            comparisons.append(
                BenchmarkComparison(
                    name=name,
                    total_return=f"{metrics['Total Return'] * 100:.2f}%",
                    sharpe=f"{metrics['Sharpe Ratio']:.2f}",
                    max_drawdown=f"{metrics['Max Drawdown'] * 100:.2f}%",
                    p_value=f"{comp.get('P-Value', 1.0):.4f}",
                )
            )

        # Statistical summary
        significant_count = len([c for c in comparisons if float(c.p_value) < 0.05])
        summary = (
            f"Compared {len(comparisons)} strategies against {baseline_name}. "
            f"{significant_count} strategies showed statistically significant outperformance."
        )

        return BenchmarkSection(comparisons=comparisons, statistical_summary=summary)


class EnsembleAdapter:
    """
    Adapter for EnsembleModel to match BenchmarkStrategy interface.
    Handles windowing for LSTM-Attention component and per-step inference.
    """

    def __init__(self, model: Any, window_size: int = 60, name: str = "Ensemble_Model"):
        """
        Initialize the adapter.
        Args:
            model: An instance of EnsembleModel.
            window_size: Lookback window size for the LSTM component.
            name: Label for the strategy.
        """
        self.model = model
        self.window_size = window_size
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Generate signals using rolling windows.
        Args:
            df: DataFrame containing OHLCV and technical indicators.
        Returns:
            np.ndarray: Array of signals.
        """
        import torch

        signals = np.zeros(len(df))
        feature_cols = [c for c in df.columns if c not in ["timestamp", "datetime"]]

        for i in range(self.window_size - 1, len(df)):
            # Current observation for PPO
            obs = df.iloc[i][feature_cols].values.astype(np.float32)

            # Sequence for LSTM
            seq_data = df.iloc[i - self.window_size + 1 : i + 1][feature_cols].values.astype(
                np.float32
            )
            seq = torch.from_numpy(seq_data).float()

            # EnsembleModel.predict returns (direction, confidence, per_algo)
            direction, _, _ = self.model.predict(obs, seq=seq)
            signals[i] = float(direction)

        return signals


class PPOAdapter:
    """
    Adapter for PPOAgent to match BenchmarkStrategy interface.
    Supports basic feature alignment and ModelAction to SignalDirection mapping.
    """

    def __init__(self, agent: Any, name: str = "PPO_Agent"):
        """
        Initialize the adapter.
        Args:
            agent: An instance of PPOAgent.
            name: Label for the strategy.
        """
        self.agent = agent
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Generate signals for the given dataset.
        """
        signals = np.zeros(len(df))
        feature_cols = [c for c in df.columns if c not in ["timestamp", "datetime"]]

        for i in range(len(df)):
            obs = df.iloc[i][feature_cols].values.astype(np.float32)
            # PPOAgent.predict returns a Signal NamedTuple
            signal = self.agent.predict(obs)
            signals[i] = float(signal.direction)

        return signals


class TransformerAdapter:
    """
    Adapter for TimeSeriesTransformer to match BenchmarkStrategy interface.
    Handles sliding window extraction and device placement.
    """

    def __init__(
        self,
        model: Any,
        window_size: int = 60,
        name: str = "Transformer_Model",
        device: str = "cpu",
    ):
        """
        Initialize the adapter.
        Args:
            model: An instance of TimeSeriesTransformer.
            window_size: Lookback window required by the model.
            name: Label for the strategy.
            device: Computing device ('cpu' or 'cuda').
        """
        self.model = model
        self.window_size = window_size
        self._name = name
        self.device = device

    @property
    def name(self) -> str:
        return self._name

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Generate signals using a sliding window approach.
        """
        import torch

        self.model.eval()
        signals = np.zeros(len(df))
        feature_cols = [c for c in df.columns if c not in ["timestamp", "datetime"]]

        # Mapping logic: 0=Buy, 1=Sell, 2=Hold (based on legacy transformer logic)
        direction_map = {0: SignalDirection.BUY, 1: SignalDirection.SELL, 2: SignalDirection.HOLD}

        with torch.no_grad():
            for i in range(self.window_size - 1, len(df)):
                window = df.iloc[i - self.window_size + 1 : i + 1][feature_cols].values
                data = torch.FloatTensor(window).unsqueeze(0).to(self.device)

                probs = self.model(data)
                action_idx = int(torch.argmax(probs, dim=-1).item())
                signals[i] = float(direction_map.get(action_idx, SignalDirection.HOLD))

        return signals
