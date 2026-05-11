"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/benchmarks.py
Benchmarking framework to compare advanced models against baseline strategies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Protocol

import numpy as np
import pandas as pd
from scipy import stats

from src.core.constants import ModelAction

if TYPE_CHECKING:
    from src.models.regime_detector import RegimeInfo


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

    def __init__(self, window: int = 14, threshold: float = 0.0):
        self.window = window
        self.threshold = threshold

    @property
    def name(self) -> str:
        return f"Momentum_ROC_{self.window}_T{self.threshold}"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        roc = df["close"].pct_change(periods=self.window)
        signals = np.zeros(len(df))
        signals[roc > self.threshold] = 1
        signals[roc < -self.threshold] = -1
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


class BuyAndHoldStrategy:
    """Simple Buy and Hold baseline."""

    @property
    def name(self) -> str:
        return "Buy_and_Hold"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Always return BUY signal."""
        return np.ones(len(df))


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


class MACDStrategy:
    """Moving Average Convergence Divergence baseline."""

    def __init__(
        self, fast_window: int = 12, slow_window: int = 26, signal_window: int = 9
    ):
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.signal_window = signal_window

    @property
    def name(self) -> str:
        return f"MACD_{self.fast_window}_{self.slow_window}_{self.signal_window}"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        exp1 = df["close"].ewm(span=self.fast_window, adjust=False).mean()
        exp2 = df["close"].ewm(span=self.slow_window, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=self.signal_window, adjust=False).mean()

        signals = np.zeros(len(df))
        signals[macd > signal_line] = 1
        signals[macd < signal_line] = -1
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


class RandomStrategy:
    """Random signal baseline (Null Hypothesis)."""

    def __init__(self, seed: int = 42):
        self.seed = seed

    @property
    def name(self) -> str:
        return f"Random_Baseline_seed_{self.seed}"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        rng = np.random.default_rng(self.seed)
        # Generate random signals: -1 (Sell), 0 (Hold), 1 (Buy)
        return rng.choice([-1, 0, 1], size=len(df))


class BenchmarkEvaluator:
    """Evaluates multiple strategies and generates comparative reports."""

    def __init__(
        self,
        df: pd.DataFrame,
        initial_balance: float = 10000.0,
        commission: float = 0.0002,
        bars_per_year: int = 252,
    ):
        self.df = df
        self.initial_balance = initial_balance
        self.commission = commission
        self.bars_per_year = bars_per_year
        self.results: dict[str, Any] = {}

    def evaluate_all(self, strategies: list[BenchmarkStrategy]) -> pd.DataFrame:
        """Run evaluation for all provided strategies."""
        summary = {}
        for strategy in strategies:
            signals = strategy.predict(self.df)
            metrics = self._calculate_metrics(signals, strategy.name)
            self.results[strategy.name] = metrics
            summary[strategy.name] = metrics

        return pd.DataFrame(summary).T

    def _calculate_metrics(self, signals: np.ndarray, name: str) -> dict[str, Any]:
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

        active_returns = daily_returns[1:] if len(daily_returns) > 1 else daily_returns

        sharpe = 0.0
        sortino = 0.0
        volatility = 0.0
        skew = 0.0
        kurt = 0.0
        var_95 = 0.0
        cvar_95 = 0.0
        tail_ratio = 0.0
        gain_to_pain = 0.0

        if len(active_returns) > 0 and np.std(active_returns) > 0:
            avg_return = np.mean(active_returns)
            std_return = np.std(active_returns)
            sharpe = avg_return / std_return * np.sqrt(self.bars_per_year)

            downside_returns = active_returns[active_returns < 0]
            downside_std = np.std(downside_returns) if len(downside_returns) > 1 else std_return
            if downside_std > 0:
                sortino = avg_return / downside_std * np.sqrt(self.bars_per_year)

            volatility = std_return * np.sqrt(self.bars_per_year)

            # Institutional Stats
            skew = float(stats.skew(active_returns))
            kurt = float(stats.kurtosis(active_returns))
            var_95 = float(np.percentile(active_returns, 5)) if len(active_returns) > 20 else 0.0
            cvar_95 = (
                float(active_returns[active_returns <= var_95].mean())
                if len(active_returns) > 20
                else 0.0
            )

            # Tail Ratio: 95th percentile / abs(5th percentile)
            p95 = np.percentile(active_returns, 95) if len(active_returns) > 20 else 0.0
            p5 = np.percentile(active_returns, 5) if len(active_returns) > 20 else 0.0
            tail_ratio = abs(p95 / p5) if abs(p5) > 1e-9 else 0.0

            # Gain-to-Pain Ratio: Sum(Gains) / Abs(Sum(Losses))
            gains = active_returns[active_returns > 0].sum()
            pains = abs(active_returns[active_returns < 0].sum())
            gain_to_pain = gains / pains if pains > 1e-9 else 0.0

        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / (peak + 1e-9)
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
        ulcer_index = float(np.sqrt(np.mean(np.square(drawdown))))
        lake_ratio = float(np.mean(drawdown))

        win_rate = 0.0
        profit_factor = 0.0
        expectancy = 0.0
        sqn = 0.0
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

            avg_pnl = np.mean(trade_pnls)
            std_pnl = np.std(trade_pnls)
            if std_pnl > 0:
                sqn = np.sqrt(len(trade_pnls)) * avg_pnl / std_pnl

        # Stability score: consistency of equity curve (R-squared of linear fit)
        stability_score = 0.0
        if len(equity) > 2:
            x = np.arange(len(equity))
            y = equity
            slope, intercept = np.polyfit(x, y, 1)
            line = slope * x + intercept
            y_var = np.sum((y - y.mean()) ** 2)
            stability_score = 1 - (np.sum((y - line) ** 2) / (y_var + 1e-9))

        calmar = total_return / max_drawdown if max_drawdown > 0 else 0.0
        common_sense_ratio = tail_ratio * (profit_factor if profit_factor != float("inf") else 1.0)

        # Store daily returns for statistical testing
        self.results[name + "_returns"] = daily_returns

        return {
            "Total Return": total_return,
            "Sharpe Ratio": sharpe,
            "Sortino Ratio": sortino,
            "Calmar Ratio": calmar,
            "Recovery Factor": calmar,
            "Volatility": volatility,
            "Max Drawdown": max_drawdown,
            "Win Rate": win_rate,
            "Profit Factor": profit_factor,
            "Expectancy": expectancy,
            "SQN": sqn,
            "Num Trades": len(trade_pnls),
            "Skewness": skew,
            "Kurtosis": kurt,
            "VaR_95": var_95,
            "CVaR_95": cvar_95,
            "Ulcer Index": ulcer_index,
            "Tail Ratio": tail_ratio,
            "Common Sense Ratio": common_sense_ratio,
            "Gain to Pain Ratio": gain_to_pain,
            "Lake Ratio": lake_ratio,
            "Stability Score": float(stability_score),
        }

    def compare_to_baseline(self, strategy_name: str, baseline_name: str) -> dict[str, Any]:
        """Perform statistical comparison between a strategy and a baseline."""
        if strategy_name not in self.results or baseline_name not in self.results:
            return {"error": "Strategy or baseline not found in results."}

        s_metrics = self.results[strategy_name]
        b_metrics = self.results[baseline_name]

        s_returns = self.results.get(strategy_name + "_returns", np.array([]))
        b_returns = self.results.get(baseline_name + "_returns", np.array([]))

        # Align lengths and handle warmup periods (trim leading zeros)
        def trim_warmup(arr: np.ndarray) -> np.ndarray:
            # Find the first non-zero element to identify end of warmup
            non_zeros = np.nonzero(arr)[0]
            return arr[non_zeros[0] :] if len(non_zeros) > 0 else arr

        s_active = trim_warmup(s_returns)
        b_active = trim_warmup(b_returns)

        # Ensure we compare the same number of data points from the end
        # to align the trading periods correctly if warmup lengths differ.
        min_len = min(len(s_active), len(b_active))
        if min_len < 2:
            return {"error": "Insufficient active returns for statistical comparison."}

        s_final = s_active[-min_len:]
        b_final = b_active[-min_len:]

        # Paired t-test on return distributions for identical market conditions
        t_stat, p_value = stats.ttest_rel(s_final, b_final)

        # Wilcoxon signed-rank test (non-parametric)
        wilcoxon_p = 1.0
        try:
            # Only run if there is variance in differences
            if not np.array_equal(s_final, b_final):
                _, wilcoxon_p = stats.wilcoxon(s_final, b_final)
        except Exception:
            wilcoxon_p = 1.0

        # Simple relative performance
        outperformance = s_metrics["Total Return"] - b_metrics["Total Return"]
        sharpe_diff = s_metrics["Sharpe Ratio"] - b_metrics["Sharpe Ratio"]

        return {
            "Outperformance": outperformance,
            "Sharpe Improvement": sharpe_diff,
            "Relative Return": outperformance / (abs(b_metrics["Total Return"]) + 1e-9),
            "T-Statistic": float(t_stat),
            "P-Value": float(p_value),
            "Wilcoxon P-Value": float(wilcoxon_p),
            "Significant": bool(p_value < 0.05 or wilcoxon_p < 0.05)
            if not np.isnan(p_value)
            else False,
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
                    profit_factor=f"{metrics.get('Profit Factor', 0.0):.2f}",
                    sqn=f"{metrics.get('SQN', 0.0):.2f}",
                    recovery_factor=f"{metrics.get('Recovery Factor', 0.0):.2f}",
                )
            )

        # Statistical summary
        significant_count = 0
        for name in self.results:
            if name.endswith("_returns") or name == baseline_name:
                continue
            comp = self.compare_to_baseline(name, baseline_name)
            if comp.get("Significant", False):
                significant_count += 1

        summary = (
            f"Compared {len(comparisons)} strategies against {baseline_name}. "
            f"{significant_count} strategies showed statistically significant outperformance "
            f"(p < 0.05 via T-test or Wilcoxon signed-rank test)."
        )

        return BenchmarkSection(comparisons=comparisons, statistical_summary=summary)


class AdapterBase:
    """Base class for model adapters to centralize common utility logic."""

    def _extract_regime_info(self, row: pd.Series) -> Optional[RegimeInfo]:
        """Extract RegimeInfo from a DataFrame row if columns exist."""
        from src.models.regime_detector import MarketRegime, RegimeInfo

        if "regime" not in row:
            return None

        try:
            return RegimeInfo(
                label=MarketRegime(row["regime"]),
                confidence=float(row.get("regime_confidence", 1.0)),
                transition_score=float(row.get("regime_transition_score", 0.0)),
                volatility_index=float(row.get("volatility_index", 1.0)),
                transition_probabilities={},
                raw_features={},
            )
        except Exception:
            return None

    def _get_feature_cols(self, df: pd.DataFrame) -> list[str]:
        """Identify feature columns by excluding non-feature metadata."""
        exclude = [
            "timestamp",
            "datetime",
            "regime",
            "regime_confidence",
            "regime_transition_score",
            "volatility_index",
        ]
        return [c for c in df.columns if c not in exclude]


class EnsembleAdapter(AdapterBase):
    """
    Adapter for EnsembleModel to match BenchmarkStrategy interface.
    Handles windowing for LSTM-Attention component and per-step inference.
    """

    def __init__(self, model: Any, window_size: int = 60, name: str = "Ensemble_Model"):
        self.model = model
        self.window_size = window_size
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        import torch

        signals = np.zeros(len(df))
        feature_cols = self._get_feature_cols(df)

        for i in range(self.window_size - 1, len(df)):
            row = df.iloc[i]
            obs = row[feature_cols].values.astype(np.float32)
            seq_data = df.iloc[i - self.window_size + 1 : i + 1][feature_cols].values.astype(
                np.float32
            )
            seq = torch.from_numpy(seq_data).float()
            regime_info = self._extract_regime_info(row)

            # EnsembleModel always supports regime_info in predict
            signal = self.model.predict(obs, seq=seq, regime_info=regime_info)
            signals[i] = float(signal.direction)

        return signals


class PPOAdapter(AdapterBase):
    """
    Adapter for PPOAgent to match BenchmarkStrategy interface.
    Supports basic feature alignment and ModelAction to SignalDirection mapping.
    """

    def __init__(self, agent: Any, name: str = "PPO_Agent"):
        self.agent = agent
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        signals = np.zeros(len(df))
        feature_cols = self._get_feature_cols(df)

        for i in range(len(df)):
            row = df.iloc[i]
            obs = row[feature_cols].values.astype(np.float32)
            regime_info = self._extract_regime_info(row)

            # PPOAgent supports **kwargs in predict
            signal = self.agent.predict(obs, regime_info=regime_info)
            signals[i] = float(signal.direction)

        return signals


class TransformerAdapter(AdapterBase):
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
        self.model = model
        self.window_size = window_size
        self._name = name
        self.device = device

    @property
    def name(self) -> str:
        return self._name

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        import torch

        self.model.eval()
        signals = np.zeros(len(df))
        feature_cols = self._get_feature_cols(df)

        with torch.no_grad():
            for i in range(self.window_size - 1, len(df)):
                row = df.iloc[i]
                window = df.iloc[i - self.window_size + 1 : i + 1][feature_cols].values
                data = torch.FloatTensor(window).unsqueeze(0).to(self.device)
                regime_info = self._extract_regime_info(row)

                if hasattr(self.model, "predict"):
                    # If predict returns a Signal object, use its direction
                    output = self.model.predict(data, regime_info=regime_info)
                    if hasattr(output, "direction"):
                        signals[i] = float(output.direction)
                        continue
                    # Otherwise assume it's probs/logits
                    probs = output
                else:
                    probs = self.model(data)

                action_idx = int(torch.argmax(probs, dim=-1).item())
                signals[i] = float(ModelAction(action_idx).to_direction())

        return signals


class LSTMAdapter(AdapterBase):
    """
    Adapter for LSTMPricePredictor to match BenchmarkStrategy interface.
    Handles sliding window extraction for sequence processing.
    """

    def __init__(
        self,
        model: Any,
        window_size: int = 60,
        name: str = "LSTM_Model",
        device: str = "cpu",
    ):
        self.model = model
        self.window_size = window_size
        self._name = name
        self.device = device

    @property
    def name(self) -> str:
        return self._name

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        import torch

        self.model.eval()
        signals = np.zeros(len(df))
        feature_cols = self._get_feature_cols(df)

        with torch.no_grad():
            for i in range(self.window_size - 1, len(df)):
                row = df.iloc[i]
                window = df.iloc[i - self.window_size + 1 : i + 1][feature_cols].values
                data = torch.FloatTensor(window).unsqueeze(0).to(self.device)
                regime_info = self._extract_regime_info(row)

                if hasattr(self.model, "predict"):
                    output = self.model.predict(data, regime_info=regime_info)
                    if hasattr(output, "direction"):
                        signals[i] = float(output.direction)
                        continue
                    probs = output
                else:
                    probs = self.model(data)

                if isinstance(probs, torch.Tensor):
                    probs = torch.softmax(probs, dim=-1).cpu().numpy()[0]

                action_idx = int(np.argmax(probs))
                signals[i] = float(ModelAction(action_idx).to_direction())

        return signals


class DreamerAdapter(AdapterBase):
    """
    Adapter for DreamerAgent to match BenchmarkStrategy interface.
    Supports state-aware inference if implemented in the agent.
    """

    def __init__(self, agent: Any, name: str = "Dreamer_Agent"):
        self.agent = agent
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        signals = np.zeros(len(df))
        feature_cols = self._get_feature_cols(df)

        if hasattr(self.agent, "reset_state"):
            self.agent.reset_state()

        for i in range(len(df)):
            row = df.iloc[i]
            obs = row[feature_cols].values.astype(np.float32)
            regime_info = self._extract_regime_info(row)

            # DreamerAgent supports **kwargs in predict
            signal = self.agent.predict(obs, regime_info=regime_info)
            direction = float(signal.direction)
            signals[i] = direction

            if hasattr(self.agent, "update_state"):
                self.agent.update_state(obs, action=int(direction), reward=0.0, is_terminal=False)

        return signals
