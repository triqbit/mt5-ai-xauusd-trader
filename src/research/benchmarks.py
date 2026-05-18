"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/benchmarks.py
Benchmarking framework to compare advanced models against baseline strategies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Protocol, runtime_checkable

import numpy as np
import pandas as pd
from scipy import stats

from src.core.constants import ModelAction

if TYPE_CHECKING:
    from src.models.regime_detector import RegimeInfo


@runtime_checkable
class BenchmarkStrategy(Protocol):
    """
    Protocol for all strategies and baselines to ensure consistent evaluation.

    Any class implementing this protocol must provide a `predict` method
    that returns trading signals and a `name` property for identification.
    """

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Generate signals for a given dataset.

        Args:
            df: DataFrame containing OHLCV data and technical indicators.

        Returns:
            np.ndarray: Array of signals (1.0: Buy, -1.0: Sell, 0.0: Hold).
        """
        ...

    @property
    def name(self) -> str:
        """
        Return the unique name of the strategy for reporting.

        Returns:
            str: Strategy name.
        """
        ...


class EMACrossoverStrategy:
    """
    Simple Exponential Moving Average (EMA) Crossover baseline.

    A trend-following strategy that generates a BUY signal when a fast EMA
    crosses above a slow EMA, and a SELL signal when it crosses below.
    """

    def __init__(self, fast_window: int = 9, slow_window: int = 21):
        """
        Initialize the EMA Crossover strategy.

        Args:
            fast_window: Period for the fast EMA.
            slow_window: Period for the slow EMA.
        """
        self.fast_window = fast_window
        self.slow_window = slow_window

    @property
    def name(self) -> str:
        return f"EMA_Crossover_{self.fast_window}_{self.slow_window}"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Predict signals using EMA crossover logic.

        Args:
            df: OHLCV DataFrame.

        Returns:
            np.ndarray: Signal array.
        """
        fast_ema = df["close"].ewm(span=self.fast_window, adjust=False).mean()
        slow_ema = df["close"].ewm(span=self.slow_window, adjust=False).mean()

        signals = np.zeros(len(df))
        signals[fast_ema > slow_ema] = 1.0
        signals[fast_ema < slow_ema] = -1.0
        return signals


class MomentumStrategy:
    """
    Momentum-based (Rate of Change) baseline.

    Generates signals based on the percentage change in price over a
    specified window.
    """

    def __init__(self, window: int = 14, threshold: float = 0.0):
        """
        Initialize the Momentum strategy.

        Args:
            window: Period for calculating Rate of Change (ROC).
            threshold: Minimum ROC required to generate a signal.
        """
        self.window = window
        self.threshold = threshold

    @property
    def name(self) -> str:
        return f"Momentum_ROC_{self.window}_T{self.threshold}"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Predict signals using ROC momentum logic.

        Args:
            df: OHLCV DataFrame.

        Returns:
            np.ndarray: Signal array.
        """
        roc = df["close"].pct_change(periods=self.window)
        signals = np.zeros(len(df))
        signals[roc > self.threshold] = 1.0
        signals[roc < -self.threshold] = -1.0
        return signals


class VolatilityBreakoutStrategy:
    """
    Bollinger Band Breakout baseline.

    A volatility-based strategy that generates a BUY signal when price
    breaks above the upper Bollinger Band and a SELL signal when it
    breaks below the lower band.
    """

    def __init__(self, window: int = 20, num_std: float = 2.0):
        """
        Initialize the Volatility Breakout strategy.

        Args:
            window: Period for the moving average and standard deviation.
            num_std: Number of standard deviations for the bands.
        """
        self.window = window
        self.num_std = num_std

    @property
    def name(self) -> str:
        return f"Volatility_Breakout_{self.window}_{self.num_std}"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Predict signals using Bollinger Band breakout logic.

        Args:
            df: OHLCV DataFrame.

        Returns:
            np.ndarray: Signal array.
        """
        rolling_mean = df["close"].rolling(window=self.window).mean()
        rolling_std = df["close"].rolling(window=self.window).std()
        upper_band = rolling_mean + (rolling_std * self.num_std)
        lower_band = rolling_mean - (rolling_std * self.num_std)

        signals = np.zeros(len(df))
        signals[df["close"] > upper_band] = 1.0
        signals[df["close"] < lower_band] = -1.0
        return signals


class NaiveDirectionalStrategy:
    """
    Naive 'Follow the Leader' (last candle direction) strategy.

    Generates a BUY signal if the last candle was bullish, and a SELL
    signal if it was bearish.
    """

    @property
    def name(self) -> str:
        return "Naive_Directional"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Predict signals based on previous candle direction.

        Args:
            df: OHLCV DataFrame.

        Returns:
            np.ndarray: Signal array.
        """
        diff = df["close"].diff()
        signals = np.zeros(len(df))
        signals[diff > 0] = 1.0
        signals[diff < 0] = -1.0
        return signals


class NaiveReversalStrategy:
    """
    Naive Mean Reversion (opposite of last candle direction) strategy.

    Generates a SELL signal if the last candle was bullish, and a BUY
    signal if it was bearish.
    """

    @property
    def name(self) -> str:
        return "Naive_Reversal"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Predict signals based on opposite of previous candle direction.

        Args:
            df: OHLCV DataFrame.

        Returns:
            np.ndarray: Signal array.
        """
        diff = df["close"].diff()
        signals = np.zeros(len(df))
        signals[diff > 0] = -1.0
        signals[diff < 0] = 1.0
        return signals


class BuyAndHoldStrategy:
    """
    Simple Buy and Hold baseline.

    Always maintains a BUY signal, representing a long-term investment.
    """

    @property
    def name(self) -> str:
        return "Buy_and_Hold"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Always return BUY signal.

        Args:
            df: OHLCV DataFrame.

        Returns:
            np.ndarray: Constant BUY signals.
        """
        return np.ones(len(df))


class RiskFilteredBaseline:
    """
    EMA Crossover strategy with a simple volatility filter.

    Only generates signals when the rolling volatility is below a
    predefined threshold, aiming to avoid choppy or extreme market states.
    """

    def __init__(
        self, fast_window: int = 9, slow_window: int = 21, vol_threshold_pct: float = 0.02
    ):
        """
        Initialize the Risk Filtered strategy.

        Args:
            fast_window: Period for fast EMA.
            slow_window: Period for slow EMA.
            vol_threshold_pct: Max allowed volatility (as decimal).
        """
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.vol_threshold_pct = vol_threshold_pct

    @property
    def name(self) -> str:
        return f"Risk_Filtered_EMA_{self.vol_threshold_pct}"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Predict signals using EMA crossover and volatility filtering.

        Args:
            df: OHLCV DataFrame.

        Returns:
            np.ndarray: Signal array.
        """
        fast_ema = df["close"].ewm(span=self.fast_window, adjust=False).mean()
        slow_ema = df["close"].ewm(span=self.slow_window, adjust=False).mean()
        volatility = df["close"].rolling(window=20).std() / df["close"]

        signals = np.zeros(len(df))
        # Only trade if volatility is below threshold
        mask = volatility < self.vol_threshold_pct
        signals[mask & (fast_ema > slow_ema)] = 1.0
        signals[mask & (fast_ema < slow_ema)] = -1.0
        return signals


class MomentumVolatilityStrategy:
    """
    Momentum baseline with a volatility filter.

    Generates signals based on Rate of Change (ROC), but only when
    rolling volatility is within an acceptable range.
    """

    def __init__(
        self, window: int = 14, threshold: float = 0.0, vol_threshold_pct: float = 0.02
    ):
        """
        Initialize the Momentum Volatility strategy.

        Args:
            window: Period for calculating ROC and volatility.
            threshold: Minimum ROC required for a signal.
            vol_threshold_pct: Max allowed volatility (as decimal).
        """
        self.window = window
        self.threshold = threshold
        self.vol_threshold_pct = vol_threshold_pct

    @property
    def name(self) -> str:
        return f"Momentum_Vol_Filtered_{self.window}_T{self.threshold}"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Predict signals using ROC and volatility filtering.

        Args:
            df: OHLCV DataFrame.

        Returns:
            np.ndarray: Signal array.
        """
        roc = df["close"].pct_change(periods=self.window)
        volatility = df["close"].rolling(window=self.window).std() / df["close"]

        signals = np.zeros(len(df))
        mask = volatility < self.vol_threshold_pct
        signals[mask & (roc > self.threshold)] = 1.0
        signals[mask & (roc < -self.threshold)] = -1.0
        return signals


class RegimeFilterBaseline:
    """
    A baseline that filters another strategy's signals based on market regime.

    Uses external regime labels (e.g., from RegimeDetector) to restrict
    the underlying strategy to specific market environments.
    """

    def __init__(
        self,
        base_strategy: BenchmarkStrategy,
        allowed_regimes: list[str],
        name: Optional[str] = None,
    ):
        """
        Initialize the Regime Filtered baseline.

        Args:
            base_strategy: The underlying strategy to filter.
            allowed_regimes: List of market regime labels where trading is permitted.
            name: Optional override for the strategy name.
        """
        self.base_strategy = base_strategy
        self.allowed_regimes = allowed_regimes
        self._name = name or f"Regime_Filtered_{base_strategy.name}"

    @property
    def name(self) -> str:
        return self._name

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Filter base signals using regime column.

        Args:
            df: OHLCV DataFrame with 'regime' column.

        Returns:
            np.ndarray: Filtered signals.
        """
        base_signals = self.base_strategy.predict(df)
        if "regime" not in df.columns:
            return np.zeros(len(df))

        # Only keep signals if regime is allowed
        # Handles both string labels and MarketRegime enum members
        mask = df["regime"].astype(str).isin(self.allowed_regimes)
        filtered_signals = np.zeros(len(df))
        filtered_signals[mask] = base_signals[mask]
        return filtered_signals


class MACDStrategy:
    """
    Moving Average Convergence Divergence (MACD) baseline.

    A trend-following momentum indicator that shows the relationship
    between two moving averages of a security's price.
    """

    def __init__(self, fast_window: int = 12, slow_window: int = 26, signal_window: int = 9):
        """
        Initialize the MACD strategy.

        Args:
            fast_window: Period for fast EMA.
            slow_window: Period for slow EMA.
            signal_window: Period for the MACD signal line.
        """
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.signal_window = signal_window

    @property
    def name(self) -> str:
        return f"MACD_{self.fast_window}_{self.slow_window}_{self.signal_window}"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Predict signals using MACD crossovers.

        Args:
            df: OHLCV DataFrame.

        Returns:
            np.ndarray: Signal array.
        """
        exp1 = df["close"].ewm(span=self.fast_window, adjust=False).mean()
        exp2 = df["close"].ewm(span=self.slow_window, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=self.signal_window, adjust=False).mean()

        signals = np.zeros(len(df))
        signals[macd > signal_line] = 1.0
        signals[macd < signal_line] = -1.0
        return signals


class MeanReversionStrategy:
    """
    RSI-based Mean Reversion baseline.

    Generates BUY signals when price is oversold and SELL signals when
    price is overbought, based on the Relative Strength Index.
    """

    def __init__(self, window: int = 14, overbought: int = 70, oversold: int = 30):
        """
        Initialize the Mean Reversion strategy.

        Args:
            window: Period for RSI calculation.
            overbought: RSI threshold for overbought state.
            oversold: RSI threshold for oversold state.
        """
        self.window = window
        self.overbought = overbought
        self.oversold = oversold

    @property
    def name(self) -> str:
        return f"Mean_Reversion_RSI_{self.window}"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Predict signals using RSI thresholds.

        Args:
            df: OHLCV DataFrame.

        Returns:
            np.ndarray: Signal array.
        """
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.window).mean()

        rs = gain / (loss + 1e-9)
        rsi = 100 - (100 / (1 + rs))

        signals = np.zeros(len(df))
        signals[rsi < self.oversold] = 1.0
        signals[rsi > self.overbought] = -1.0
        return signals


class RandomStrategy:
    """
    Random signal baseline (Null Hypothesis).

    Generates stochastic BUY, SELL, or HOLD signals. Used to verify
    if a strategy's performance is statistically better than random chance.
    """

    def __init__(self, seed: int = 42):
        """
        Initialize the Random strategy.

        Args:
            seed: Random seed for reproducibility.
        """
        self.seed = seed

    @property
    def name(self) -> str:
        return f"Random_Baseline_seed_{self.seed}"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Generate random signals.

        Args:
            df: OHLCV DataFrame.

        Returns:
            np.ndarray: Random signals (-1, 0, 1).
        """
        rng = np.random.default_rng(self.seed)
        return rng.choice([-1.0, 0.0, 1.0], size=len(df))


class DonchianChannelStrategy:
    """
    Donchian Channel breakout baseline.

    Generates signals when the price breaks out of the high/low range
    of the previous N bars.
    """

    def __init__(self, window: int = 20):
        """
        Initialize the Donchian Breakout strategy.

        Args:
            window: Period for calculating high/low channel.
        """
        self.window = window

    @property
    def name(self) -> str:
        return f"Donchian_Breakout_{self.window}"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Predict signals using Donchian Channel breakouts.

        Args:
            df: OHLCV DataFrame.

        Returns:
            np.ndarray: Signal array.
        """
        upper_channel = df["high"].rolling(window=self.window).max()
        lower_channel = df["low"].rolling(window=self.window).min()

        signals = np.zeros(len(df))
        signals[df["close"] >= upper_channel.shift(1)] = 1.0
        signals[df["close"] <= lower_channel.shift(1)] = -1.0
        return signals


class ADXStrategy:
    """
    Trend-following strategy based on the Average Directional Index (ADX).

    Uses ADX to confirm trend strength and Directional Indicators (DI)
    to determine trend direction.
    """

    def __init__(self, window: int = 14, adx_threshold: float = 25.0):
        """
        Initialize the ADX strategy.

        Args:
            window: Period for ADX and DI calculations.
            adx_threshold: Minimum ADX required to confirm a strong trend.
        """
        self.window = window
        self.adx_threshold = adx_threshold

    @property
    def name(self) -> str:
        return f"ADX_Trend_{self.window}_T{self.adx_threshold}"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Predict signals using ADX and DI.

        Args:
            df: OHLCV DataFrame.

        Returns:
            np.ndarray: Signal array.
        """
        try:
            import talib

            high, low, close = (
                df["high"].values.astype(float),
                df["low"].values.astype(float),
                df["close"].values.astype(float),
            )
            adx = talib.ADX(high, low, close, timeperiod=self.window)
            plus_di = talib.PLUS_DI(high, low, close, timeperiod=self.window)
            minus_di = talib.MINUS_DI(high, low, close, timeperiod=self.window)
        except (ImportError, Exception):
            # Fallback: Simple manual DI calculation
            diff = df["close"].diff()
            plus_dm = diff.where(diff > 0, 0.0).rolling(self.window).mean()
            minus_dm = (-diff.where(diff < 0, 0.0)).rolling(self.window).mean()
            tr = (
                pd.concat(
                    [
                        df["high"] - df["low"],
                        (df["high"] - df["close"].shift(1)).abs(),
                        (df["low"] - df["close"].shift(1)).abs(),
                    ],
                    axis=1,
                )
                .max(axis=1)
                .rolling(self.window)
                .mean()
            )

            plus_di = 100 * (plus_dm / (tr + 1e-9))
            minus_di = 100 * (minus_dm / (tr + 1e-9))
            dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9)
            adx = dx.rolling(self.window).mean().values
            plus_di = plus_di.values
            minus_di = minus_di.values

        signals = np.zeros(len(df))
        strong_trend = adx > self.adx_threshold
        signals[strong_trend & (plus_di > minus_di)] = 1.0
        signals[strong_trend & (minus_di > plus_di)] = -1.0
        return signals


class SuperTrendStrategy:
    """
    SuperTrend baseline strategy.

    A trend-following indicator that uses ATR to define bands around the
    median price. It switches direction when the close price crosses the bands.
    """

    def __init__(self, window: int = 10, multiplier: float = 3.0):
        """
        Initialize the SuperTrend strategy.

        Args:
            window: Period for ATR calculation.
            multiplier: Multiplier for the ATR-based offset.
        """
        self.window = window
        self.multiplier = multiplier

    @property
    def name(self) -> str:
        return f"SuperTrend_{self.window}_{self.multiplier}"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Predict signals using SuperTrend logic.

        Args:
            df: OHLCV DataFrame.

        Returns:
            np.ndarray: Signal array.
        """
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values

        # Median Price
        hl2 = (high + low) / 2

        # ATR calculation
        tr1 = high - low
        prev_close = pd.Series(close).shift(1).values
        tr2 = np.abs(high - prev_close)
        tr3 = np.abs(low - prev_close)
        tr = np.nan_to_num(np.maximum(tr1, np.maximum(tr2, tr3)), nan=tr1[0])
        atr = pd.Series(tr).rolling(window=self.window).mean().values

        upper_band = hl2 + (self.multiplier * atr)
        lower_band = hl2 - (self.multiplier * atr)

        signals = np.zeros(len(df))
        trend = 1  # 1 for UP, -1 for DOWN

        # Refined SuperTrend logic to prevent bands from moving unfavorably
        for i in range(self.window, len(df)):
            if close[i - 1] > upper_band[i - 1]:
                trend = 1
            elif close[i - 1] < lower_band[i - 1]:
                trend = -1

            if trend == 1:
                if lower_band[i] < lower_band[i - 1]:
                    lower_band[i] = lower_band[i - 1]
                signals[i] = 1.0
            else:
                if upper_band[i] > upper_band[i - 1]:
                    upper_band[i] = upper_band[i - 1]
                signals[i] = -1.0

        return signals


class LondonBreakoutStrategy:
    """
    London Breakout baseline strategy.

    Trades the breakout of the Asian session range (usually 00:00 to 08:00 GMT).
    Specifically optimized for XAUUSD which often has high volatility at London open.
    """

    def __init__(self, range_start: str = "00:00", range_end: str = "08:00"):
        """
        Initialize the London Breakout strategy.

        Args:
            range_start: Start of the range definition period (HH:MM).
            range_end: End of the range definition period (HH:MM).
        """
        self.range_start = range_start
        self.range_end = range_end

    @property
    def name(self) -> str:
        return f"London_Breakout_{self.range_start.replace(':', '')}_{self.range_end.replace(':', '')}"

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Predict signals using London Breakout logic.

        Args:
            df: OHLCV DataFrame with DatetimeIndex.

        Returns:
            np.ndarray: Signal array.
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            return np.zeros(len(df))

        signals = np.zeros(len(df))

        # Group by day to handle each daily breakout independently
        for _, day_data in df.groupby(df.index.date):
            # Identify the range definition session
            session_range = day_data.between_time(self.range_start, self.range_end)
            if session_range.empty:
                continue

            high_target = session_range["high"].max()
            low_target = session_range["low"].min()

            # Analyze price action after the range period
            after_range = day_data[day_data.index > session_range.index[-1]]

            day_end_pos = df.index.get_loc(day_data.index[-1])

            for idx, row in after_range.iterrows():
                # Locate position in original signal array
                pos = df.index.get_loc(idx)
                if row["close"] > high_target:
                    # Maintain signal until end of trading day
                    signals[pos : day_end_pos + 1] = 1.0
                    break  # One breakout trade per day
                elif row["close"] < low_target:
                    # Maintain signal until end of trading day
                    signals[pos : day_end_pos + 1] = -1.0
                    break

        return signals


class BenchmarkEvaluator:
    """
    Evaluates multiple strategies and generates comparative reports.

    Provides high-fidelity backtesting of signals with realistic
    costs (commission, slippage) and statistical validation of results.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        initial_balance: float = 10000.0,
        commission: float = 0.0002,
        slippage: float = 0.0001,
        bars_per_year: int = 252,
    ):
        """
        Initialize the BenchmarkEvaluator.

        Args:
            df: DataFrame containing OHLCV data.
            initial_balance: Starting account balance.
            commission: Transaction fee as a decimal (e.g., 0.0002 for 2 bps).
            slippage: Execution slippage as a decimal per trade (e.g., 0.0001 for 1 bp).
            bars_per_year: Number of bars in a trading year (for Sharpe/Sortino scaling).
        """
        self.df = df
        self.initial_balance = initial_balance
        self.commission = commission
        self.slippage = slippage
        self.bars_per_year = bars_per_year
        self.results: dict[str, Any] = {}

    def evaluate_all(self, strategies: list[BenchmarkStrategy]) -> pd.DataFrame:
        """
        Run evaluation for all provided strategies.

        Args:
            strategies: List of objects implementing BenchmarkStrategy.

        Returns:
            pd.DataFrame: Summary table of performance metrics.
        """
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

        position = 0.0
        entry_equity = self.initial_balance

        for i in range(1, n):
            target_pos = float(signals[i - 1])
            prev_price = close[i - 1]
            current_price = close[i]
            current_equity = equity[i - 1]

            # Handle transitions (Closures / Reversals / Entries)
            if target_pos != position:
                # Total cost for the transition: Commission + Slippage
                transition_cost = self.commission + self.slippage

                # If closing an existing position
                if position != 0:
                    current_equity *= 1 - transition_cost
                    trade_pnls.append(current_equity - entry_equity)

                # If opening a new position
                if target_pos != 0:
                    current_equity *= 1 - transition_cost
                    entry_equity = current_equity

                position = target_pos

            # Update equity based on market movement
            if position == 1.0:
                change = (current_price - prev_price) / prev_price
                current_equity *= 1 + change
            elif position == -1.0:
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

        # Initialize defaults
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
            _res = stats.linregress(x, y)
            stability_score = float(_res.rvalue**2)

        calmar = total_return / max_drawdown if max_drawdown > 0 else 0.0
        common_sense_ratio = tail_ratio * (profit_factor if profit_factor != float("inf") else 1.0)
        omega_ratio = gain_to_pain  # Threshold of 0.0

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
            "Omega Ratio": omega_ratio,
            "Lake Ratio": lake_ratio,
            "Stability Score": float(stability_score),
        }

    def compare_to_baseline(self, strategy_name: str, baseline_name: str) -> dict[str, Any]:
        """
        Perform statistical comparison between a strategy and a baseline.

        Uses paired t-tests and Wilcoxon signed-rank tests to determine
        if outperformance is statistically significant.

        Args:
            strategy_name: Name of the strategy to test.
            baseline_name: Name of the baseline for comparison.

        Returns:
            dict[str, Any]: Statistical comparison metrics.
        """
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
        min_len = min(len(s_active), len(b_active))
        if min_len < 2:
            return {"error": "Insufficient active returns for statistical comparison."}

        s_final = s_active[-min_len:]
        b_final = b_active[-min_len:]

        outperformance = s_metrics["Total Return"] - b_metrics["Total Return"]
        sharpe_diff = s_metrics["Sharpe Ratio"] - b_metrics["Sharpe Ratio"]

        # Information Ratio: (Rp - Rb) / TrackingError
        diff_returns = s_final - b_final
        avg_diff = np.mean(diff_returns)
        std_diff = np.std(diff_returns)
        info_ratio = (
            (avg_diff / std_diff * np.sqrt(self.bars_per_year)) if std_diff > 1e-12 else 0.0
        )

        note = ""

        # Check for zero-variance differences to prevent NaN in statistical tests
        diff = s_final - b_final
        if np.all(diff == 0):
            t_stat, p_value, wilcoxon_p = 0.0, 1.0, 1.0
            note = "Identical return distributions"
        elif np.std(diff) < 1e-12:
            # Constant non-zero difference
            t_stat, p_value, wilcoxon_p = 0.0, 0.0, 0.0
            note = "Constant outperformance"
        else:
            # Paired t-test on return distributions
            t_stat, p_value = stats.ttest_rel(s_final, b_final)

            # Wilcoxon signed-rank test (non-parametric)
            wilcoxon_p = 1.0
            try:
                _, wilcoxon_p = stats.wilcoxon(s_final, b_final)
            except Exception:
                wilcoxon_p = 1.0

        # Handle potential NaNs from stats functions
        p_value = float(p_value) if not np.isnan(p_value) else 1.0
        wilcoxon_p = float(wilcoxon_p) if not np.isnan(wilcoxon_p) else 1.0
        t_stat = float(t_stat) if not np.isnan(t_stat) else 0.0

        return {
            "Outperformance": outperformance,
            "Sharpe Improvement": sharpe_diff,
            "Information Ratio": info_ratio,
            "Relative Return": outperformance / (abs(b_metrics["Total Return"]) + 1e-9),
            "T-Statistic": t_stat,
            "P-Value": p_value,
            "Wilcoxon P-Value": wilcoxon_p,
            "Significant": bool(p_value < 0.05 or wilcoxon_p < 0.05),
            "Note": note,
        }

    def to_report_section(self, baseline_name: str) -> Any:
        """
        Convert results into a BenchmarkSection for the ResearchReporter.

        Args:
            baseline_name: The strategy to use as the primary baseline.

        Returns:
            BenchmarkSection: Pydantic model for reporting.
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
                    calmar_ratio=f"{metrics.get('Calmar Ratio', 0.0):.2f}",
                    expected_shortfall=f"{metrics.get('CVaR_95', 0.0):.2%}",
                    ulcer_index=f"{metrics.get('Ulcer Index', 0.0):.2f}",
                    lake_ratio=f"{metrics.get('Lake Ratio', 0.0):.2f}",
                    tail_ratio=f"{metrics.get('Tail Ratio', 0.0):.2f}",
                    common_sense_ratio=f"{metrics.get('Common Sense Ratio', 0.0):.2f}",
                    information_ratio=f"{comp.get('Information Ratio', 0.0):.2f}",
                    omega_ratio=f"{metrics.get('Omega Ratio', 0.0):.2f}",
                )
            )

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

    Handles windowing for LSTM-Attention component and per-step inference
    with regime-awareness.
    """

    def __init__(self, model: Any, window_size: int = 60, name: str = "Ensemble_Model"):
        """
        Initialize the Ensemble adapter.

        Args:
            model: EnsembleModel instance.
            window_size: Sequence length for models requiring history.
            name: Identification name.
        """
        self.model = model
        self.window_size = window_size
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Generate ensemble signals.

        Args:
            df: OHLCV DataFrame.

        Returns:
            np.ndarray: Signal array.
        """
        import torch

        signals = np.zeros(len(df))
        if len(df) < self.window_size:
            return signals

        feature_cols = self._get_feature_cols(df)

        for i in range(self.window_size - 1, len(df)):
            row = df.iloc[i]
            obs = row[feature_cols].values.astype(np.float32)
            seq_data = df.iloc[i - self.window_size + 1 : i + 1][feature_cols].values.astype(
                np.float32
            )
            seq = torch.from_numpy(seq_data).float()
            regime_info = self._extract_regime_info(row)

            signal = self.model.predict(obs, seq=seq, regime_info=regime_info)
            signals[i] = float(signal.direction)

        return signals


class PPOAdapter(AdapterBase):
    """
    Adapter for PPOAgent to match BenchmarkStrategy interface.

    Supports basic feature alignment and ModelAction to SignalDirection mapping.
    """

    def __init__(self, agent: Any, name: str = "PPO_Agent"):
        """
        Initialize the PPO adapter.

        Args:
            agent: PPOAgent instance.
            name: Identification name.
        """
        self.agent = agent
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Generate PPO signals.

        Args:
            df: OHLCV DataFrame.

        Returns:
            np.ndarray: Signal array.
        """
        signals = np.zeros(len(df))
        feature_cols = self._get_feature_cols(df)

        for i in range(len(df)):
            row = df.iloc[i]
            obs = row[feature_cols].values.astype(np.float32)
            regime_info = self._extract_regime_info(row)

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
        """
        Initialize the Transformer adapter.

        Args:
            model: TimeSeriesTransformer instance.
            window_size: Lookback window length.
            name: Identification name.
            device: Computing device.
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
        Generate Transformer signals.

        Args:
            df: OHLCV DataFrame.

        Returns:
            np.ndarray: Signal array.
        """
        import torch

        self.model.eval()
        signals = np.zeros(len(df))
        if len(df) < self.window_size:
            return signals

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
        """
        Initialize the LSTM adapter.

        Args:
            model: LSTMModel instance.
            window_size: Lookback window length.
            name: Identification name.
            device: Computing device.
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
        Generate LSTM signals.

        Args:
            df: OHLCV DataFrame.

        Returns:
            np.ndarray: Signal array.
        """
        import torch

        self.model.eval()
        signals = np.zeros(len(df))
        if len(df) < self.window_size:
            return signals

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
        """
        Initialize the Dreamer adapter.

        Args:
            agent: DreamerAgent instance.
            name: Identification name.
        """
        self.agent = agent
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Generate Dreamer signals.

        Args:
            df: OHLCV DataFrame.

        Returns:
            np.ndarray: Signal array.
        """
        signals = np.zeros(len(df))
        feature_cols = self._get_feature_cols(df)

        if hasattr(self.agent, "reset_state"):
            self.agent.reset_state()

        for i in range(len(df)):
            row = df.iloc[i]
            obs = row[feature_cols].values.astype(np.float32)
            regime_info = self._extract_regime_info(row)

            signal = self.agent.predict(obs, regime_info=regime_info)
            direction = float(signal.direction)
            signals[i] = direction

            if hasattr(self.agent, "update_state"):
                self.agent.update_state(obs, action=int(direction), reward=0.0, is_terminal=False)

        return signals
