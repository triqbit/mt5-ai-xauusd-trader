"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/utils/synthetic_data.py
Deterministic scenario generator for testing system robustness across market regimes.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

import numpy as np
import pandas as pd

from src.core.constants import EventCategory, EventImpact, SignalDirection
from src.core.schemas import TradeSignal
from src.data.event_models import MacroEvent, RiskStatus
from src.models.base_model import Signal
from src.models.regime_detector import MarketRegime, RegimeInfo
from src.trading.capital_allocator import AllocationRequest, StrategyConfig

if TYPE_CHECKING:
    from src.core.trade_logger import TradeLogger
    from src.models.dynamic_ensemble import DynamicEnsemble


class ScenarioGenerator:
    """
    Generates deterministic synthetic OHLCV data for testing.
    Ensures reproducibility via seeding.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def generate(
        self,
        n_steps: int = 100,
        regime: Literal[
            "trending",
            "ranging",
            "volatile",
            "gapping",
            "malformed",
            "whipsaw",
            "stale",
            "flash_crash",
            "regime_shift",
            "mean_reversion",
            "low_volatility_drift",
            "news_shock",
            "noisy",
            "missing_data",
        ] = "ranging",
        start_price: float = 2300.0,
        trend_strength: float = 0.001,
        volatility: float = 0.002,
        start_date: datetime | str | None = None,
        freq: str = "5min",
    ) -> pd.DataFrame:
        """
        Main entry point for data generation.
        """
        self._current_start_date = start_date
        self._current_freq = freq

        if regime == "trending":
            return self._generate_trending(n_steps, start_price, trend_strength, volatility)
        if regime == "ranging":
            return self._generate_ranging(n_steps, start_price, volatility)
        if regime == "volatile":
            return self._generate_volatile(n_steps, start_price, volatility)
        if regime == "gapping":
            return self._generate_gapping(n_steps, start_price, volatility)
        if regime == "malformed":
            return self._generate_malformed(n_steps, start_price)
        if regime == "whipsaw":
            return self._generate_whipsaw(n_steps, start_price, volatility)
        if regime == "stale":
            return self._generate_stale(n_steps, start_price)
        if regime == "flash_crash":
            return self._generate_flash_crash(n_steps, start_price, volatility)
        if regime == "regime_shift":
            return self._generate_regime_shift(n_steps, start_price, volatility)
        if regime == "mean_reversion":
            return self._generate_mean_reversion(n_steps, start_price, volatility)
        if regime == "low_volatility_drift":
            return self._generate_low_volatility_drift(n_steps, start_price)
        if regime == "news_shock":
            return self._generate_news_shock(n_steps, start_price)
        if regime == "noisy":
            return self._generate_noisy(n_steps, start_price, volatility)
        if regime == "missing_data":
            return self._generate_missing_data(n_steps, start_price, volatility)
        raise ValueError(f"Unknown regime: {regime}")

    def _generate_base(self, n_steps: int, start_price: float, returns: np.ndarray) -> pd.DataFrame:
        """Helper to convert returns to OHLCV with price continuity."""
        # Calculate close prices from cumulative returns
        close_prices = start_price * np.exp(np.cumsum(returns))

        # Open price of bar i is the close of bar i-1 (Price Continuity)
        open_prices = np.zeros(n_steps)
        open_prices[0] = start_price
        if n_steps > 1:
            open_prices[1:] = close_prices[:-1]

        # Generate realistic intraday noise for High/Low
        # High must be >= max(open, close)
        # Low must be <= min(open, close)
        vol = np.abs(returns) + 0.0005  # Ensure some minimum range
        high_noise = self.rng.exponential(vol * 0.5, n_steps)
        low_noise = self.rng.exponential(vol * 0.5, n_steps)

        high_prices = np.maximum(open_prices, close_prices) + high_noise
        low_prices = np.minimum(open_prices, close_prices) - low_noise

        # Generate spread (in pips)
        # Standard spread is 0.5 - 1.5 pips for XAUUSD in normal conditions
        base_spread = 0.8
        spread_noise = self.rng.uniform(0, 0.4, n_steps)
        spreads = base_spread + spread_noise

        # Generate volume correlated with price movement
        # Base volume 100-500
        base_volume = self.rng.integers(100, 500, n_steps)
        # Spike volume on large moves
        move_magnitude = np.abs(returns)
        volume_spike = (move_magnitude * 200000).astype(int)
        tick_volumes = base_volume + volume_spike

        df = pd.DataFrame(
            {
                "open": open_prices,
                "high": high_prices,
                "low": low_prices,
                "close": close_prices,
                "tick_volume": tick_volumes,
                "spread_pips": spreads,
            }
        )

        # Apply datetime index if provided
        start_date = getattr(self, "_current_start_date", None)
        if start_date:
            df.index = pd.date_range(start=start_date, periods=n_steps, freq=self._current_freq)

        return df

    def generate_multi_timeframe(
        self,
        n_steps_base: int = 1000,
        base_freq: str = "1min",
        timeframes: list[str] | None = None,
        regime: str = "trending",
        start_date: datetime | str | None = None,
        **kwargs: Any,
    ) -> dict[str, pd.DataFrame]:
        """
        Generates consistent OHLC data across multiple timeframes by resampling.
        Ensures that high-TF bars are perfectly aligned with low-TF bars.
        """
        if timeframes is None:
            timeframes = ["M5", "M15", "H1"]
        if start_date is None:
            start_date = datetime(2024, 5, 22, 0, 0, tzinfo=UTC)

        # 1. Generate base high-resolution data (e.g., M1)
        df_base = self.generate(
            n_steps=n_steps_base, regime=regime, freq=base_freq, start_date=start_date, **kwargs
        )

        results = {base_freq: df_base}

        # 2. Resample for each requested timeframe
        for tf in timeframes:
            # Map MT5 timeframe codes to pandas freq
            # M5 -> 5min, H1 -> 1h, etc.
            match = re.match(r"([A-Z]+)(\d+)", tf)
            if match:
                unit_code, value = match.groups()
                unit = {"M": "min", "H": "h", "D": "D", "W": "W", "MN": "ME"}.get(unit_code, "min")
                resample_freq = f"{value}{unit}"
            else:
                # Fallback for single letter codes if any
                resample_freq = (
                    tf.replace("M", "min").replace("H", "h").replace("D", "D").replace("W", "W")
                )

            resampled = (
                df_base.resample(resample_freq)
                .agg(
                    {
                        "open": "first",
                        "high": "max",
                        "low": "min",
                        "close": "last",
                        "tick_volume": "sum",
                    }
                )
                .dropna()
            )

            results[tf] = resampled

        return results

    def inject_faults(
        self,
        df: pd.DataFrame,
        fault_type: Literal["stale", "outliers", "zero_volume", "gaps", "high_spread"],
        prob: float = 0.05,
    ) -> pd.DataFrame:
        """Injects operational faults into an existing dataset."""
        df = df.copy()
        n = len(df)
        if n < 2:
            return df

        indices = self.rng.choice(n, size=max(1, int(n * prob)), replace=False)

        if fault_type == "stale":
            # Bar matches previous bar exactly (frozen data)
            for idx in indices:
                if idx > 0:
                    df.iloc[idx] = df.iloc[idx - 1]
        elif fault_type == "outliers":
            # Ghost ticks / extreme price spikes (e.g. fat finger or bad feed)
            for idx in indices:
                side = self.rng.choice([-1, 1])
                multiplier = 1 + (0.1 * side)  # 10% outlier
                df.iloc[idx, df.columns.get_loc("high")] *= multiplier
                df.iloc[idx, df.columns.get_loc("low")] *= multiplier
                df.iloc[idx, df.columns.get_loc("close")] *= multiplier
        elif fault_type == "zero_volume":
            # Price moves but volume is reported as zero
            df.iloc[indices, df.columns.get_loc("tick_volume")] = 0
        elif fault_type == "gaps":
            # Price jump without continuity (slippage or weekend gap)
            for idx in sorted(indices):
                if idx < n - 1:
                    gap = self.rng.normal(0, 0.01) * df.iloc[idx]["close"]
                    df.iloc[idx + 1 :, df.columns.get_loc("open")] += gap
                    df.iloc[idx + 1 :, df.columns.get_loc("high")] += gap
                    df.iloc[idx + 1 :, df.columns.get_loc("low")] += gap
                    df.iloc[idx + 1 :, df.columns.get_loc("close")] += gap
        elif fault_type == "high_spread":
            # Spread spikes (e.g. news or rollover)
            # Standard halt is usually around 2.0 pips for XAUUSD
            df.iloc[indices, df.columns.get_loc("spread_pips")] *= 5.0

        return df

    def _generate_trending(
        self, n_steps: int, start_price: float, trend_strength: float, volatility: float
    ) -> pd.DataFrame:
        returns = self.rng.normal(trend_strength, volatility, n_steps)
        return self._generate_base(n_steps, start_price, returns)

    def _generate_ranging(
        self, n_steps: int, start_price: float, volatility: float
    ) -> pd.DataFrame:
        returns = self.rng.normal(0, volatility, n_steps)
        return self._generate_base(n_steps, start_price, returns)

    def _generate_volatile(
        self, n_steps: int, start_price: float, volatility: float
    ) -> pd.DataFrame:
        # Mix of normal and high-variance returns
        returns = self.rng.normal(0, volatility, n_steps)
        spikes = self.rng.choice([0, 1], size=n_steps, p=[0.9, 0.1])
        returns += spikes * self.rng.normal(0, volatility * 5, n_steps)
        return self._generate_base(n_steps, start_price, returns)

    def _generate_gapping(
        self, n_steps: int, start_price: float, volatility: float
    ) -> pd.DataFrame:
        returns = self.rng.normal(0, volatility, n_steps)
        gaps = self.rng.choice([0, 1], size=n_steps, p=[0.95, 0.05])
        returns += gaps * self.rng.choice([-0.02, 0.02], size=n_steps)  # 2% gaps
        return self._generate_base(n_steps, start_price, returns)

    def _generate_whipsaw(
        self, n_steps: int, start_price: float, volatility: float
    ) -> pd.DataFrame:
        """Breakout followed by immediate sharp reversal."""
        mid = n_steps // 2
        returns = self.rng.normal(0, volatility, n_steps)
        # Bullish breakout
        returns[mid - 5 : mid] = 0.01
        # Bearish reversal
        returns[mid : mid + 5] = -0.015
        return self._generate_base(n_steps, start_price, returns)

    def _generate_stale(self, n_steps: int, start_price: float) -> pd.DataFrame:
        """Frozen price scenario."""
        returns = np.zeros(n_steps)
        return self._generate_base(n_steps, start_price, returns)

    def _generate_flash_crash(
        self, n_steps: int, start_price: float, volatility: float
    ) -> pd.DataFrame:
        """Extreme drop followed by partial recovery."""
        returns = self.rng.normal(0, volatility, n_steps)
        mid = n_steps // 2
        # Rapid crash
        returns[mid : mid + 5] = -0.04  # -4% per step for 5 steps (~ -18% total)
        # Partial recovery
        returns[mid + 5 : mid + 10] = 0.02
        return self._generate_base(n_steps, start_price, returns)

    def _generate_regime_shift(
        self, n_steps: int, start_price: float, volatility: float
    ) -> pd.DataFrame:
        """Transition from ranging to highly volatile."""
        mid = n_steps // 2
        returns_ranging = self.rng.normal(0, volatility, mid)
        returns_volatile = self.rng.normal(0, volatility * 4, n_steps - mid)
        returns = np.concatenate([returns_ranging, returns_volatile])
        return self._generate_base(n_steps, start_price, returns)

    def _generate_mean_reversion(
        self, n_steps: int, start_price: float, volatility: float
    ) -> pd.DataFrame:
        """Oscillating price process with high z-score and low efficiency ratio."""
        # Oscillate around start_price
        prices = np.zeros(n_steps)
        prices[0] = start_price
        for i in range(1, n_steps):
            prices[i] = (
                start_price
                + (start_price * 0.01 * (1 if i % 2 == 0 else -1))
                + self.rng.normal(0, 0.0001 * start_price)
            )

        # Force high z-score at the end: sudden jump
        prices[-1] = start_price * 1.05

        returns = np.diff(prices) / prices[:-1]
        returns = np.insert(returns, 0, 0)
        return self._generate_base(n_steps, start_price, returns)

    def _generate_low_volatility_drift(self, n_steps: int, start_price: float) -> pd.DataFrame:
        """Small constant trend with minimal noise and low ATR."""
        # Aim for ATR ratio < 0.9. We need to reduce current volatility relative to historical.
        # Generate some high volatility first, then drop it.
        mid = n_steps // 2
        returns_high_vol = self.rng.normal(0, 0.01, mid)
        returns_drift = np.full(n_steps - mid, 0.00004) + self.rng.normal(
            0, 0.000001, n_steps - mid
        )
        returns = np.concatenate([returns_high_vol, returns_drift])
        return self._generate_base(n_steps, start_price, returns)

    def _generate_news_shock(self, n_steps: int, start_price: float) -> pd.DataFrame:
        """Extreme spike at the end to trigger NEWS_SHOCK (> 2.5 ATR ratio)."""
        # We need a very low-vol background to make the spike stand out
        # Generate 100 steps of very low vol, then a massive spike
        n_steps = max(n_steps, 101)
        returns = self.rng.normal(0, 0.00005, n_steps)
        # NEWS_SHOCK requires high Efficiency Ratio (> 0.7).
        # We must ensure the return sequence is sustained or extremely efficient.
        # But detector uses Kaufman ER which is (net change) / (sum of abs changes).
        # A single massive spike at the end should have high ER.
        # Let's ensure volatility of volatility (vov) is also high (> 0.1).
        returns[-1] = 0.15  # Massive 15% move in one bar
        return self._generate_base(n_steps, start_price, returns)

    def _generate_malformed(self, n_steps: int, start_price: float) -> pd.DataFrame:
        df = self._generate_ranging(n_steps, start_price, 0.001)

        # Inject anomalies
        # 1. High < Low
        df.loc[0, "high"] = df.loc[0, "low"] - 10.0

        # 2. Negative price
        df.loc[1, "close"] = -100.0

        # 3. NaNs
        df.loc[2, "open"] = np.nan

        # 4. Zero volume
        df.loc[3, "tick_volume"] = 0

        return df

    def _generate_noisy(self, n_steps: int, start_price: float, volatility: float) -> pd.DataFrame:
        """Ranging data with frequent extreme outliers (spikes)."""
        returns = self.rng.normal(0, volatility, n_steps)
        # 5% of bars are extreme spikes
        spikes = self.rng.choice([0, 1, -1], size=n_steps, p=[0.95, 0.025, 0.025])
        returns += spikes * volatility * 20
        return self._generate_base(n_steps, start_price, returns)

    def _generate_missing_data(
        self, n_steps: int, start_price: float, volatility: float
    ) -> pd.DataFrame:
        """Data with random NaN holes."""
        df = self._generate_ranging(n_steps, start_price, volatility)
        # 5% missing values per column
        for col in ["open", "high", "low", "close", "tick_volume"]:
            mask = self.rng.choice([True, False], size=n_steps, p=[0.05, 0.95])
            df.loc[mask, col] = np.nan
        return df


class BacktestScenarioBuilder:
    """
    Generates deterministic price sequences designed to verify backtest metrics.
    """

    def __init__(self, seed: int = 42):
        self.gen = ScenarioGenerator(seed=seed)

    def drawdown_recovery(self, n_steps: int = 200, start_price: float = 10000.0) -> pd.DataFrame:
        """
        Creates a 10% drawdown followed by a 20% gain.
        Useful for verifying Max Drawdown and Recovery Factor.
        """
        mid = n_steps // 2
        quarter = mid // 2

        # Start flat
        returns = np.zeros(n_steps)
        # Drop 10% over 'quarter' steps
        returns[quarter:mid] = np.log(0.9) / (mid - quarter)
        # Gain 20% from that low over 'mid' steps
        returns[mid:] = np.log(1.2) / (n_steps - mid)

        return self.gen._generate_base(n_steps, start_price, returns)

    def wick_traps(self, n_steps: int = 100, start_price: float = 2300.0) -> pd.DataFrame:
        """
        Creates bars where both SL and TP levels are touched.
        Verifies conservative SL-first exit policy in backtester.
        """
        df = self.gen.generate(n_steps, regime="ranging", start_price=start_price)
        # Inject wick traps: massive high and massive low on the same bar
        trap_indices = [10, 30, 50]
        for idx in trap_indices:
            real_idx = df.index[idx]
            close = df.loc[real_idx, "close"]
            df.loc[real_idx, "high"] = close + 100.0
            df.loc[real_idx, "low"] = close - 100.0

        return df

    def steady_sharpe(self, n_steps: int = 500, start_price: float = 2300.0) -> pd.DataFrame:
        """
        Near-perfect linear trend with minimal noise.
        Should produce high Sharpe and Profit Factor.
        """
        returns = np.full(n_steps, 0.0001)  # Steady 0.01% gain per bar
        # Add tiny amount of noise
        returns += self.gen.rng.normal(0, 0.00001, n_steps)
        return self.gen._generate_base(n_steps, start_price, returns)


class RiskScenarioBuilder:
    """
    Generates deterministic sequences of TradeSignal objects for risk testing.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def consecutive_losses(
        self,
        n_signals: int = 5,
        symbol: str = "XAUUSD",
        start_price: float = 2000.0,
    ) -> list[TradeSignal]:
        """Generates a sequence of signals likely to hit SL."""
        signals = []
        # Use a fixed Wednesday timestamp to avoid SESSION_CLOSED during CI runs on weekends
        fixed_timestamp = datetime(2024, 5, 22, 12, 0, tzinfo=UTC)
        for i in range(n_signals):
            price = start_price - (i * 10)
            signals.append(
                TradeSignal(
                    symbol=symbol,
                    direction=1,  # BUY
                    entry_price=price,
                    stop_loss=price - 20,
                    take_profit=price + 40,
                    lot_size=0.1,
                    algorithm="ensemble",
                    confidence=0.7,
                    timestamp=fixed_timestamp,
                )
            )
        return signals

    def ensemble_dissent(
        self,
        symbol: str = "XAUUSD",
        price: float = 2000.0,
    ) -> list[TradeSignal]:
        """Generates signals representing conflicting model votes."""
        # Use a fixed Wednesday timestamp to avoid SESSION_CLOSED during CI runs on weekends
        fixed_timestamp = datetime(2024, 5, 22, 12, 0, tzinfo=UTC)
        return [
            TradeSignal(
                symbol=symbol,
                direction=1,
                entry_price=price,
                stop_loss=price - 10,
                take_profit=price + 20,
                lot_size=0.1,
                algorithm="ppo",
                confidence=0.9,
                timestamp=fixed_timestamp,
            ),
            TradeSignal(
                symbol=symbol,
                direction=-1,
                entry_price=price,
                stop_loss=price + 10,
                take_profit=price - 20,
                lot_size=0.1,
                algorithm="lstm",
                confidence=0.8,
                timestamp=fixed_timestamp,
            ),
        ]

    def daily_loss_breach(
        self,
        symbol: str = "XAUUSD",
        price: float = 2000.0,
        n_losses: int = 3,
    ) -> list[TradeSignal]:
        """Generates signals that, if lost, would breach the daily loss limit."""
        signals = []
        # Use a fixed Wednesday timestamp to avoid SESSION_CLOSED during CI runs on weekends
        fixed_timestamp = datetime(2024, 5, 22, 12, 0, tzinfo=UTC)
        for _ in range(n_losses):
            signals.append(
                TradeSignal(
                    symbol=symbol,
                    direction=1,
                    entry_price=price,
                    stop_loss=price - 50,  # Significant loss
                    take_profit=price + 100,
                    lot_size=1.0,  # Large lot to amplify PnL impact
                    algorithm="ensemble",
                    confidence=0.8,
                    timestamp=fixed_timestamp,
                )
            )
        return signals

    def drawdown_circuit_breaker(
        self,
        symbol: str = "XAUUSD",
        price: float = 2000.0,
    ) -> list[TradeSignal]:
        """Generates signals for testing the 15% peak-to-valley circuit breaker."""
        # Use a fixed Wednesday timestamp to avoid SESSION_CLOSED during CI runs on weekends
        fixed_timestamp = datetime(2024, 5, 22, 12, 0, tzinfo=UTC)
        # A single very large losing trade or multiple trades
        return [
            TradeSignal(
                symbol=symbol,
                direction=1,
                entry_price=price,
                stop_loss=price - 500,  # Massive stop loss
                take_profit=price + 1000,
                lot_size=2.0,
                algorithm="ensemble",
                confidence=0.9,
                timestamp=fixed_timestamp,
            )
        ]


class ExecutionScenarioBuilder:
    """
    Generates (TradeSignal, DataFrame) pairs tailored to test specific ExecutionFilter layers.
    """

    def __init__(self, seed: int = 42):
        self.gen = ScenarioGenerator(seed=seed)

    def passing_buy(self, symbol: str = "XAUUSD") -> tuple[TradeSignal, pd.DataFrame]:
        """A clean BUY signal in a moderate bullish trend."""
        # Lower trend strength to avoid RSI > 75
        df = self.gen.generate(
            n_steps=300, regime="trending", trend_strength=0.0002, volatility=0.0005
        )
        # Use a fixed Wednesday timestamp to avoid SESSION_CLOSED during CI runs on weekends
        fixed_timestamp = datetime(2024, 5, 22, 12, 0, tzinfo=UTC)

        # Ensure enough data for indicators
        signal = TradeSignal(
            symbol=symbol,
            direction=1,
            entry_price=df["close"].iloc[-1],
            stop_loss=df["close"].iloc[-1] - 10,
            take_profit=df["close"].iloc[-1] + 20,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=0.8,
            timestamp=fixed_timestamp,
        )
        return signal, df

    def atr_failure(self, symbol: str = "XAUUSD") -> tuple[TradeSignal, pd.DataFrame]:
        """Signal during extreme volatility spike (ATR failure)."""
        df = self.gen.generate(n_steps=200, regime="ranging", volatility=0.0005)
        # Spike ATR at the end by blowing up the range of the last candle
        last_idx = df.index[-1]
        df.loc[last_idx, "high"] = df.loc[last_idx, "close"] + 50.0
        df.loc[last_idx, "low"] = df.loc[last_idx, "close"] - 50.0

        signal = TradeSignal(
            symbol=symbol,
            direction=1,
            entry_price=df["close"].iloc[-1],
            stop_loss=df["close"].iloc[-1] - 5,
            take_profit=df["close"].iloc[-1] + 10,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=0.7,
        )
        return signal, df

    def session_violation(
        self, symbol: str = "XAUUSD"
    ) -> tuple[TradeSignal, pd.DataFrame, datetime]:
        """BUY signal on a Saturday (market closed)."""
        signal, df = self.passing_buy(symbol)
        # 2024-06-01 is a Saturday
        sat = datetime(2024, 6, 1, 12, 0, tzinfo=UTC)
        # Handle frozen Pydantic model
        signal = signal.model_copy(update={"timestamp": sat})
        return signal, df, sat

    def drawdown_violation(self, symbol: str = "XAUUSD") -> tuple[TradeSignal, pd.DataFrame, float]:
        """Signal with excessive drawdown (e.g., 0.35)."""
        signal, df = self.passing_buy(symbol)
        return signal, df, 0.35

    def confidence_violation(self, symbol: str = "XAUUSD") -> tuple[TradeSignal, pd.DataFrame]:
        """Signal with confidence below threshold (0.4)."""
        signal, df = self.passing_buy(symbol)
        # Ensure open market time and handle frozen Pydantic model
        signal = signal.model_copy(
            update={"timestamp": datetime(2024, 5, 22, 12, 0, tzinfo=UTC), "confidence": 0.4}
        )
        return signal, df

    def signal_flicker_violation(self, symbol: str = "XAUUSD") -> list[TradeSignal]:
        """A sequence of oscillating signals (BUY, SELL, BUY, SELL, ...)."""
        signals = []
        base_price = 2300.0
        # Use a fixed Wednesday timestamp to avoid SESSION_CLOSED during CI runs on weekends
        fixed_timestamp = datetime(2024, 5, 22, 12, 0, tzinfo=UTC)
        for i in range(10):
            direction = 1 if i % 2 == 0 else -1
            signals.append(
                TradeSignal(
                    symbol=symbol,
                    direction=direction,
                    entry_price=base_price,
                    stop_loss=base_price
                    - (100 * direction),  # Large SL to avoid price-based violations
                    take_profit=base_price + (200 * direction),
                    lot_size=0.1,
                    algorithm="ensemble",
                    confidence=0.7,  # Lower confidence to avoid RSI-like failures, but above 0.6
                    timestamp=fixed_timestamp,
                )
            )
        return signals

    def performance_violation(
        self, symbol: str = "XAUUSD"
    ) -> tuple[TradeSignal, pd.DataFrame, Any]:
        """Signal with a mocked trade logger reporting low win rate."""
        signal, df = self.passing_buy(symbol)

        # We define a simple dummy class to avoid importing MagicMock at the top level of src
        class DummyLogger:
            def read_performance_report(self):
                # win_rate below 0.45 and total_trades >= 20 to trigger Performance Guard
                return {"win_rate": 0.3, "total_trades": 25}

        return signal, df, DummyLogger()

    def trend_failure(self, symbol: str = "XAUUSD") -> tuple[TradeSignal, pd.DataFrame]:
        """BUY signal in a BEARISH trend (Trend Angle failure)."""
        df = self.gen.generate(n_steps=200, regime="trending", trend_strength=-0.005)
        signal = TradeSignal(
            symbol=symbol,
            direction=1,
            entry_price=df["close"].iloc[-1],
            stop_loss=df["close"].iloc[-1] - 10,
            take_profit=df["close"].iloc[-1] + 20,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=0.7,
        )
        return signal, df

    def ema_out_of_sequence(self, symbol: str = "XAUUSD") -> tuple[TradeSignal, pd.DataFrame]:
        """BUY signal where EMAs are not correctly stacked."""
        # Use a trending regime so it passes Trend Angle (slope > 0)
        df = self.gen.generate(n_steps=300, regime="trending", trend_strength=0.0005)

        # Manually break the EMA sequence in the last row to trigger failure
        # For BUY, we need EMA8 > EMA21 > EMA50 > EMA200. We'll swap 8 and 21.
        # Note: ExecutionFilter computes EMAs if not present in columns.
        # We can pre-calculate and put them in the DF to force the check.
        df["base_M5_ema_8"] = df["close"].ewm(span=8, adjust=False).mean()
        df["base_M5_ema_21"] = df["close"].ewm(span=21, adjust=False).mean()
        df["base_M5_ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
        df["base_M5_ema_200"] = df["close"].ewm(span=200, adjust=False).mean()

        last_idx = df.index[-1]
        # Swap so EMA21 > EMA8 -> Failure for BUY
        val8 = df.loc[last_idx, "base_M5_ema_8"]
        val21 = df.loc[last_idx, "base_M5_ema_21"]
        df.loc[last_idx, "base_M5_ema_8"] = val21
        df.loc[last_idx, "base_M5_ema_21"] = val8

        signal = TradeSignal(
            symbol=symbol,
            direction=1,
            entry_price=df["close"].iloc[-1],
            stop_loss=df["close"].iloc[-1] - 10,
            take_profit=df["close"].iloc[-1] + 20,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=0.7,
        )
        return signal, df

    def momentum_failure(self, symbol: str = "XAUUSD") -> tuple[TradeSignal, pd.DataFrame]:
        """BUY signal when RSI is too high (overbought)."""
        # Rapid vertical move spikes RSI.
        # Needs to pass ATR, TREND_ANGLE, EMA_SEQUENCE first.
        df = self.gen.generate(n_steps=300, regime="trending", trend_strength=0.0005)
        # Spike the very end to push RSI over 75 without blowing up EMA sequence too much
        # or just use a very strong trend that eventually hits RSI 80+
        df_spike = self.gen.generate(
            n_steps=50, regime="trending", trend_strength=0.01, start_price=df["close"].iloc[-1]
        )
        df = pd.concat([df, df_spike]).iloc[-300:]

        signal = TradeSignal(
            symbol=symbol,
            direction=1,
            entry_price=df["close"].iloc[-1],
            stop_loss=df["close"].iloc[-1] - 10,
            take_profit=df["close"].iloc[-1] + 20,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=0.7,
        )
        return signal, df


class ModelHealthGenerator:
    """Generates deterministic model health metrics for testing."""

    @staticmethod
    def perfect_health() -> dict[str, float]:
        """Metrics well within safety limits."""
        return {"drift": 0.01, "accuracy": 0.92, "calibration": 0.05}

    @staticmethod
    def degraded_drift() -> dict[str, float]:
        """Breaches drift threshold."""
        return {"drift": 0.35, "accuracy": 0.88, "calibration": 0.08}

    @staticmethod
    def degraded_accuracy() -> dict[str, float]:
        """Breaches accuracy floor."""
        return {"drift": 0.02, "accuracy": 0.45, "calibration": 0.10}

    @staticmethod
    def degraded_calibration() -> dict[str, float]:
        """Breaches calibration threshold."""
        return {"drift": 0.02, "accuracy": 0.85, "calibration": 0.45}


class RegimeScenarioBuilder:
    """
    Generates deterministic datasets specifically designed to trigger each MarketRegime.
    """

    def __init__(self, seed: int = 42):
        self.gen = ScenarioGenerator(seed=seed)

    def trending(self) -> pd.DataFrame:
        """Triggers MarketRegime.TRENDING."""
        return self.gen.generate(
            n_steps=150, regime="trending", trend_strength=0.002, volatility=0.0005
        )

    def ranging(self) -> pd.DataFrame:
        """Triggers MarketRegime.RANGING."""
        return self.gen.generate(n_steps=150, regime="ranging", volatility=0.0005)

    def mean_reversion(self) -> pd.DataFrame:
        """Triggers MarketRegime.MEAN_REVERSION."""
        return self.gen.generate(n_steps=150, regime="mean_reversion", volatility=0.001)

    def volatile_breakout(self) -> pd.DataFrame:
        """Triggers MarketRegime.VOLATILE_BREAKOUT."""
        # Need ATR ratio > 1.25 and ER > 0.5.
        mid = 100
        n_steps = 150
        returns_low = self.gen.rng.normal(0, 0.0001, mid)
        returns_high = self.gen.rng.normal(0.005, 0.005, n_steps - mid)
        returns = np.concatenate([returns_low, returns_high])
        return self.gen._generate_base(n_steps, 2300.0, returns)

    def low_volatility_drift(self) -> pd.DataFrame:
        """Triggers MarketRegime.LOW_VOLATILITY_DRIFT."""
        return self.gen.generate(n_steps=150, regime="low_volatility_drift")

    def news_shock(self) -> pd.DataFrame:
        """Triggers MarketRegime.NEWS_SHOCK."""
        return self.gen.generate(n_steps=150, regime="news_shock")

    def volatile_breakout_sustained(self, n_steps: int = 150) -> pd.DataFrame:
        """Triggers MarketRegime.VOLATILE_BREAKOUT with a sustained expansion."""
        mid = n_steps * 2 // 3
        returns_low = self.gen.rng.normal(0, 0.0001, mid)
        # Sustained 1% moves for expansion phase
        returns_high = self.gen.rng.normal(0.01, 0.001, n_steps - mid)
        returns = np.concatenate([returns_low, returns_high])
        return self.gen._generate_base(n_steps, 2300.0, returns)


class PortfolioScenarioBuilder:
    """
    Generates deterministic multi-strategy portfolio states and request sequences
    for testing the CapitalAllocator and RiskManager.
    """

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def concentration_risk_cascade(self) -> tuple[list[StrategyConfig], list[AllocationRequest]]:
        """
        Creates a scenario where multiple strategies hit symbol and family limits.
        - 3 strategies on XAUUSD (Symbol concentration)
        - 3 strategies in RL family (Family concentration)
        """
        configs = [
            StrategyConfig(
                strategy_id="gold_rl_1", symbol="XAUUSD", model_family="RL", capital_cap=100000
            ),
            StrategyConfig(
                strategy_id="gold_rl_2", symbol="XAUUSD", model_family="RL", capital_cap=100000
            ),
            StrategyConfig(
                strategy_id="gold_rl_3", symbol="XAUUSD", model_family="RL", capital_cap=100000
            ),
            StrategyConfig(
                strategy_id="eur_rl_1", symbol="EURUSD", model_family="RL", capital_cap=100000
            ),
        ]
        # Sequential requests that should eventually trigger concentration limits
        requests = [
            AllocationRequest(strategy_id="gold_rl_1", risk_pct=0.15),
            AllocationRequest(strategy_id="gold_rl_2", risk_pct=0.15),
            AllocationRequest(
                strategy_id="gold_rl_3", risk_pct=0.15
            ),  # Should hit XAUUSD 0.4 limit
            AllocationRequest(strategy_id="eur_rl_1", risk_pct=0.15),  # Should hit RL 0.4 limit
        ]
        return configs, requests

    def performance_rebalancing_sequence(self) -> list[dict]:
        """
        Returns a sequence of (strategy_id, pnl, request_risk) to test adaptive rebalancing.
        """
        return [
            {"strategy_id": "strat_a", "pnl": 500.0, "request": 0.02},  # Win -> Scale up
            {"strategy_id": "strat_a", "pnl": 600.0, "request": 0.02},  # Win -> Scale up more
            {"strategy_id": "strat_a", "pnl": -1000.0, "request": 0.02},  # Loss -> Scale down
            {"strategy_id": "strat_a", "pnl": -1000.0, "request": 0.02},  # Loss -> Scale down
            {"strategy_id": "strat_a", "pnl": -1000.0, "request": 0.02},  # Hits cooling-off
        ]

    def high_heat_portfolio(self) -> tuple[list[StrategyConfig], list[AllocationRequest]]:
        """
        Generates requests that push total portfolio heat toward and past 0.7 limit.
        """
        configs = [
            StrategyConfig(
                strategy_id=f"strat_{i}",
                symbol=f"SYM_{i}",
                model_family=f"FAM_{i}",
                capital_cap=100000,
            )
            for i in range(5)
        ]
        requests = [AllocationRequest(strategy_id=f"strat_{i}", risk_pct=0.15) for i in range(5)]
        # 5 * 0.15 = 0.75 (> 0.7)
        return configs, requests

    def diversified_unbalanced_setup(self) -> list[StrategyConfig]:
        """
        Mixed performance states for testing diversification score and report generation.
        """
        return [
            StrategyConfig(
                strategy_id="alpha",
                symbol="XAUUSD",
                model_family="RL",
                performance_multiplier=1.8,
                capital_cap=100000,
            ),
            StrategyConfig(
                strategy_id="beta",
                symbol="EURUSD",
                model_family="LSTM",
                performance_multiplier=0.6,
                capital_cap=100000,
            ),
            StrategyConfig(
                strategy_id="gamma",
                symbol="GBPUSD",
                model_family="Transformer",
                performance_multiplier=1.0,
                capital_cap=100000,
            ),
        ]


class MacroScenarioBuilder:
    """
    Generates deterministic MacroEvent objects for risk testing.
    """

    @staticmethod
    def nfp_shock(timestamp: datetime | None = None) -> MacroEvent:
        """Non-Farm Payrolls high impact event."""
        if timestamp is None:
            timestamp = datetime(2024, 5, 22, 12, 30, tzinfo=UTC)
        return MacroEvent(
            name="Non-Farm Payrolls",
            category=EventCategory.NFP,
            impact=EventImpact.HIGH,
            timestamp=timestamp,
            symbol_impact=["XAUUSD", "USD"],
            description="Major employment data release.",
        )

    @staticmethod
    def fomc_meeting(timestamp: datetime | None = None) -> MacroEvent:
        """FOMC Rate Decision critical impact event."""
        if timestamp is None:
            timestamp = datetime(2024, 5, 22, 18, 0, tzinfo=UTC)
        return MacroEvent(
            name="FOMC Rate Decision",
            category=EventCategory.FOMC,
            impact=EventImpact.CRITICAL,
            timestamp=timestamp,
            symbol_impact=["XAUUSD", "USD"],
            description="Federal Reserve interest rate decision.",
        )

    @staticmethod
    def geopolitical_crisis(timestamp: datetime | None = None) -> MacroEvent:
        """Geopolitical event with persistent risk."""
        if timestamp is None:
            timestamp = datetime(2024, 5, 22, 0, 0, tzinfo=UTC)
        return MacroEvent(
            name="Geopolitical Tension",
            category=EventCategory.GEOPOLITICAL,
            impact=EventImpact.HIGH,
            timestamp=timestamp,
            symbol_impact=["XAUUSD"],
            description="Sudden escalation in regional conflict.",
        )


class SystemContextBuilder:
    """
    Generates integrated test contexts: (OHLCV, list[MacroEvent], RiskStatus).
    """

    def __init__(self, seed: int = 42):
        self.price_gen = ScenarioGenerator(seed=seed)
        self.macro_gen = MacroScenarioBuilder()

    def normal_trading(self) -> tuple[pd.DataFrame, list[MacroEvent], RiskStatus]:
        """Context for standard, low-risk trading."""
        # Use a fixed Wednesday to avoid weekend sessions
        start_date = datetime(2024, 5, 22, 8, 0, tzinfo=UTC)
        df = self.price_gen.generate(n_steps=200, regime="ranging", start_date=start_date)

        return df, [], RiskStatus(is_blocked=False, risk_multiplier=1.0)

    def high_impact_macro_event(self) -> tuple[pd.DataFrame, list[MacroEvent], RiskStatus]:
        """Context during a High-Impact news release (NFP)."""
        start_date = datetime(2024, 5, 22, 11, 0, tzinfo=UTC)
        df = self.price_gen.generate(n_steps=200, regime="news_shock", start_date=start_date)

        # NFP happens at 12:30 UTC, which is during our data window
        event = self.macro_gen.nfp_shock(timestamp=datetime(2024, 5, 22, 12, 30, tzinfo=UTC))

        # RiskStatus should reflect the news block
        risk = RiskStatus(
            is_blocked=True,
            risk_multiplier=0.0,
            active_events=[event],
            blocking_events=[event],
            reason="High impact NFP news block.",
        )
        return df, [event], risk

    def extreme_volatility_with_risk_block(
        self,
    ) -> tuple[pd.DataFrame, list[MacroEvent], RiskStatus]:
        """Context with extreme price action and defensive risk positioning."""
        start_date = datetime(2024, 5, 22, 16, 0, tzinfo=UTC)
        df = self.price_gen.generate(n_steps=200, regime="flash_crash", start_date=start_date)

        event = self.macro_gen.fomc_meeting(timestamp=datetime(2024, 5, 22, 18, 0, tzinfo=UTC))

        risk = RiskStatus(
            is_blocked=True,
            risk_multiplier=0.0,
            active_events=[event],
            blocking_events=[event],
            reason="Critical FOMC meeting in progress.",
        )
        return df, [event], risk


class RegimeTransitionScenarioBuilder:
    """
    Generates deterministic price sequences that transition between market regimes.
    Useful for testing transition_score and adaptive risk logic.
    """

    def __init__(self, seed: int = 42):
        self.gen = ScenarioGenerator(seed=seed)

    def ranging_to_news_shock(
        self, n_steps: int = 200, start_price: float = 2300.0
    ) -> pd.DataFrame:
        """Stable ranging followed by a sudden extreme news spike."""
        mid = n_steps // 2
        # Ranging phase: very low vol
        returns_ranging = self.gen.rng.normal(0, 0.00001, mid)
        # News shock phase: massive spike (sustained for a few bars to affect rolling windows)
        returns_news = self.gen.rng.normal(0, 0.0001, n_steps - mid)
        returns_news[0:5] = 0.08  # 8% spike sustained for 5 bars to blow up ATR ratio

        returns = np.concatenate([returns_ranging, returns_news])
        return self.gen._generate_base(n_steps, start_price, returns)

    def trending_to_reversal(self, n_steps: int = 200, start_price: float = 2300.0) -> pd.DataFrame:
        """Strong bullish trend followed by exhaustion and sharp reversal."""
        mid = n_steps // 2
        # Bullish trend: steady growth
        returns_trend = self.gen.rng.normal(0.001, 0.0002, mid)
        # Reversal: sharp drop
        returns_reversal = self.gen.rng.normal(-0.0015, 0.0003, n_steps - mid)

        returns = np.concatenate([returns_trend, returns_reversal])
        return self.gen._generate_base(n_steps, start_price, returns)

    def volatile_to_ranging(self, n_steps: int = 200, start_price: float = 2300.0) -> pd.DataFrame:
        """Extreme volatility phase that cools down into stable ranging."""
        mid = n_steps // 2
        # Volatile phase: high variance
        returns_volatile = self.gen.rng.normal(0, 0.01, mid)
        # Cooling down to ranging: very low variance
        returns_ranging = self.gen.rng.normal(0, 0.0001, n_steps - mid)

        returns = np.concatenate([returns_volatile, returns_ranging])
        return self.gen._generate_base(n_steps, start_price, returns)


class AdversarialScenarioBuilder:
    """
    Generates deterministic price sequences designed to trick filters or trigger edge cases.
    """

    def __init__(self, seed: int = 42):
        self.gen = ScenarioGenerator(seed=seed)

    def wick_trap_cascade(self, n_steps: int = 50, start_price: float = 2300.0) -> pd.DataFrame:
        """
        Sequence of bars with small bodies but massive alternating wicks.
        Tests stop-loss sensitivity and noise filtering.
        """
        df = self.gen.generate(
            n_steps, regime="ranging", start_price=start_price, volatility=0.0001
        )
        for i in range(10, 20):
            idx = df.index[i]
            # Alternate upward and downward wicks
            if i % 2 == 0:
                df.at[idx, "high"] = df.at[idx, "close"] + 20.0
            else:
                df.at[idx, "low"] = df.at[idx, "close"] - 20.0
        return df

    def liquidity_void(self, n_steps: int = 50, start_price: float = 2300.0) -> pd.DataFrame:
        """
        Price jumps between bars without continuity (gaps).
        Tests gap-detection and continuity-enforcement logic.
        """
        df = self.gen.generate(
            n_steps, regime="ranging", start_price=start_price, volatility=0.0005
        )
        # Inject major gaps
        gap_indices = [15, 30, 45]
        for idx_pos in gap_indices:
            if idx_pos < len(df):
                idx = df.index[idx_pos]
                gap = 50.0 if idx_pos % 2 == 0 else -50.0
                df.loc[idx:, ["open", "high", "low", "close"]] += gap
        return df

    def vov_explosion(self, n_steps: int = 150, start_price: float = 2300.0) -> pd.DataFrame:
        """
        Ranging data where the volatility itself is extremely unstable.
        Tests volatility-of-volatility (VoV) and stability metrics.
        """
        returns = np.zeros(n_steps)
        for i in range(n_steps):
            # Variance itself oscillates violently between extreme states
            vol = 0.05 if (i // 10) % 2 == 0 else 0.00001
            returns[i] = self.gen.rng.normal(0, vol)
        return self.gen._generate_base(n_steps, start_price, returns)

    def ema_crossover_flicker(
        self, n_steps: int = 100, start_price: float = 2300.0
    ) -> pd.DataFrame:
        """
        Oscillations triggering frequent indicator crossovers.
        Tests 'signal flicker' and 'consistency' guards.
        """
        # We want price to dance around the EMA21
        # First, generate a base to establish EMA
        df = self.gen.generate(n_steps=200, regime="ranging", start_price=start_price)
        # Calculate EMA manually for targeting
        ema21 = df["close"].ewm(span=21, adjust=False).mean().iloc[-1]

        # Now generate flickering steps
        flicker_returns = []
        current_p = ema21
        for i in range(n_steps):
            # Oscillate by 0.01% above and below the target
            target = ema21 * (1.0001 if i % 2 == 0 else 0.9999)
            ret = np.log(target / current_p)
            flicker_returns.append(ret)
            current_p = target

        df_flicker = self.gen._generate_base(n_steps, ema21, np.array(flicker_returns))
        return pd.concat([df.iloc[-100:], df_flicker])

    def rsi_boundary_oscillation(
        self, n_steps: int = 100, start_price: float = 2300.0
    ) -> pd.DataFrame:
        """
        Pinning RSI at thresholds (e.g., 70-75) to test boundary conditions.
        """
        # Start with a trend to push RSI up
        df_trend = self.gen.generate(
            n_steps=100, regime="trending", trend_strength=0.001, start_price=start_price
        )
        last_price = df_trend["close"].iloc[-1]

        # Oscillate to keep RSI near 70
        osc_returns = []
        current_p = last_price
        for i in range(n_steps):
            # Small moves to maintain momentum without overextending
            ret = 0.0001 if i % 2 == 0 else -0.00005
            osc_returns.append(ret)
            current_p *= np.exp(ret)

        df_osc = self.gen._generate_base(n_steps, last_price, np.array(osc_returns))
        return pd.concat([df_trend, df_osc])


class AnomalyScenarioBuilder:
    """
    Generates deterministic sequences for technical anomalies.
    """

    def __init__(self, seed: int = 42):
        self.gen = ScenarioGenerator(seed=seed)

    def ghost_spikes(self, n_steps: int = 100, start_price: float = 2300.0) -> pd.DataFrame:
        """
        Extreme wicks with no impact on closing price.
        Tests robustness of noise filters vs real volatility.
        """
        df = self.gen.generate(
            n_steps, regime="ranging", start_price=start_price, volatility=0.0001
        )
        # Inject ghost spikes: massive high/low but close remains near open
        for i in [20, 40, 60, 80]:
            if i < len(df):
                idx = df.index[i]
                if i % 40 == 20:
                    df.at[idx, "high"] = df.at[idx, "open"] + 50.0
                else:
                    df.at[idx, "low"] = df.at[idx, "open"] - 50.0
        return df

    def stale_data_with_noise(
        self, n_steps: int = 100, start_price: float = 2300.0
    ) -> pd.DataFrame:
        """
        Simulates data feed freezes with minimal floating-point jitter.
        Tests 'stale data' detection logic.
        """
        df = self.gen.generate(n_steps, regime="ranging", start_price=start_price, volatility=0.0)
        # Add tiny jitter (1e-6)
        noise = self.gen.rng.uniform(-0.000001, 0.000001, n_steps)
        df["close"] += noise
        df["open"] = df["close"].shift(1).fillna(start_price)
        df["high"] = df[["open", "close"]].max(axis=1) + 0.000001
        df["low"] = df[["open", "close"]].min(axis=1) - 0.000001
        return df


class InstitutionalFlowGenerator:
    """
    Generates deterministic price sequences simulating institutional market behavior.
    """

    def __init__(self, seed: int = 42):
        self.gen = ScenarioGenerator(seed=seed)

    def stop_hunting(self, n_steps: int = 100, start_price: float = 2300.0) -> pd.DataFrame:
        """
        Simulates a 'stop hunt': price moves steadily, dips sharply below a support
        level to trigger stops, then reverses rapidly.
        """
        mid = n_steps // 2
        # Phase 1: Steady ranging
        returns_ranging = self.gen.rng.normal(0, 0.0001, mid)

        # Phase 2: Sharp dip (stop hunt)
        returns_dip = np.zeros(10)
        returns_dip[:5] = -0.005  # Sharp drop
        returns_dip[5:] = 0.007  # Rapid reversal

        # Phase 3: Resume ranging or trend
        remaining = n_steps - mid - 10
        if remaining > 0:
            returns_end = self.gen.rng.normal(0.0002, 0.0001, remaining)
            returns = np.concatenate([returns_ranging, returns_dip, returns_end])
        else:
            returns = np.concatenate([returns_ranging, returns_dip])[:n_steps]

        return self.gen._generate_base(n_steps, start_price, returns)

    def iceberg_absorption(self, n_steps: int = 100, start_price: float = 2300.0) -> pd.DataFrame:
        """
        Simulates price hitting a large hidden (iceberg) limit order.
        Results in multiple failed attempts to break a level with high volume
        and low price progress.
        """
        mid = n_steps // 2
        iceberg_level = start_price * 1.01

        returns = np.zeros(n_steps)
        current_price = start_price

        # Phase 1: Trend towards iceberg
        for i in range(mid):
            ret = 0.0005 + self.gen.rng.normal(0, 0.0001)
            current_price *= np.exp(ret)
            returns[i] = ret
            if current_price >= iceberg_level:
                # Early hit
                break

        # Phase 2: Absorption at iceberg
        for i in range(mid, n_steps):
            # Attempt to break up
            ret = 0.001 + self.gen.rng.normal(0, 0.0002)
            temp_price = current_price * np.exp(ret)

            if temp_price > iceberg_level:
                # Absorbed! Small bounce back
                ret = np.log(iceberg_level / current_price) - 0.0002
                current_price *= np.exp(ret)
            else:
                current_price = temp_price

            returns[i] = ret

        df = self.gen._generate_base(n_steps, start_price, returns)

        # Inject high volume during absorption phase
        df.iloc[mid:, df.columns.get_loc("tick_volume")] *= 5

        return df

    def trend_exhaustion(self, n_steps: int = 150, start_price: float = 2300.0) -> pd.DataFrame:
        """
        Simulates an exhausting trend: strong growth, followed by a parabolic
        blow-off top (climax) and a sharp collapse.
        """
        one_third = n_steps // 3

        # Phase 1: Steady trend
        returns_steady = self.gen.rng.normal(0.0005, 0.0001, one_third)

        # Phase 2: Parabolic blow-off
        returns_climax = np.linspace(0.001, 0.005, one_third) + self.gen.rng.normal(
            0, 0.0005, one_third
        )

        # Phase 3: Sharp reversal
        returns_collapse = self.gen.rng.normal(-0.004, 0.001, n_steps - 2 * one_third)

        returns = np.concatenate([returns_steady, returns_climax, returns_collapse])
        return self.gen._generate_base(n_steps, start_price, returns)


class LifecycleScenarioBuilder:
    """
    Generates multi-stage deterministic price and event sequences.
    Simulates operational lifecycles: Normal -> Failure -> Recovery.
    """

    def __init__(self, seed: int = 42):
        self.gen = ScenarioGenerator(seed=seed)
        self.macro = MacroScenarioBuilder()

    def flash_crash_recovery_cycle(
        self, n_steps: int = 300
    ) -> tuple[pd.DataFrame, list[MacroEvent]]:
        """
        Sequence:
        - 1/3: Ranging (Normal)
        - Mid: Flash Crash (Fault)
        - Final 1/3: Flat then recovery (Stabilization)
        """
        one_third = n_steps // 3

        # 1. Normal Ranging
        df_normal = self.gen.generate(n_steps=one_third, regime="ranging", volatility=0.0005)

        # 2. Flash Crash
        df_crash = self.gen.generate(
            n_steps=one_third, regime="flash_crash", start_price=df_normal["close"].iloc[-1]
        )

        # 3. Stabilization and Recovery
        df_recovery = self.gen.generate(
            n_steps=n_steps - 2 * one_third,
            regime="trending",
            start_price=df_crash["close"].iloc[-1],
            trend_strength=0.0005,
            volatility=0.0001,
        )

        df = pd.concat([df_normal, df_crash, df_recovery])
        # Fix index if start_date was provided, otherwise it's just integer index
        df.index = range(len(df))

        return df, []

    def news_block_lifecycle(
        self, n_steps: int = 200
    ) -> tuple[pd.DataFrame, list[MacroEvent], datetime]:
        """
        Sequence:
        - Ranging -> High Impact News -> News Shock Price Action -> Post-news stabilization.
        """
        mid = n_steps // 2
        start_date = datetime(2024, 5, 22, 11, 0, tzinfo=UTC)

        df = self.gen.generate(n_steps=n_steps, regime="news_shock", start_date=start_date)

        # News event at 12:30 (middle of the 200-bar window if freq is 5min)
        # 200 * 5min = 1000min ~= 16h. 11:00 + 500min ~= 19:20.
        # Let's adjust event time to be 11:00 + mid * 5min
        event_time = start_date + pd.Timedelta(minutes=mid * 5)
        event = self.macro.nfp_shock(timestamp=event_time)

        return df, [event], event_time


class ExecutionQualityScenarioBuilder:
    """
    Generates deterministic sets of historical trade data for performance testing.
    Useful for verifying win rate guards, slippage alerts, and cost analysis.
    """

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def toxic_flow_sequence(self, n_trades: int = 30) -> list[dict[str, Any]]:
        """
        Generates trades with consistently high negative slippage and low win rate.
        Simulates 'toxic' execution environment or bad alpha.
        """
        trades = []
        for i in range(n_trades):
            # 80% loss rate
            is_win = self.rng.random() < 0.2
            pnl = self.rng.uniform(10, 50) if is_win else self.rng.uniform(-100, -20)

            # High slippage: 2.0 to 5.0 pips (threshold is usually 1.0)
            slippage = self.rng.uniform(2.0, 5.0)

            trades.append(
                {
                    "ticket": 1000 + i,
                    "symbol": "XAUUSD",
                    "direction": 1,
                    "pnl": pnl,
                    "slippage_pips": slippage,
                    "execution_latency_ms": self.rng.uniform(500, 2000),
                    "status": "CLOSED",
                }
            )
        return trades

    def high_performance_sequence(self, n_trades: int = 30) -> list[dict[str, Any]]:
        """
        Generates trades with 70% win rate and positive edge capture.
        """
        trades = []
        for i in range(n_trades):
            is_win = self.rng.random() < 0.7
            pnl = self.rng.uniform(50, 200) if is_win else self.rng.uniform(-30, -10)

            # Low slippage: 0.1 to 0.5 pips
            slippage = self.rng.uniform(0.1, 0.5)

            trades.append(
                {
                    "ticket": 2000 + i,
                    "symbol": "XAUUSD",
                    "direction": 1,
                    "pnl": pnl,
                    "slippage_pips": slippage,
                    "execution_latency_ms": self.rng.uniform(50, 150),
                    "status": "CLOSED",
                }
            )
        return trades

    def edge_case_fills(self) -> list[dict[str, Any]]:
        """
        Specific scenarios:
        1. Zero slippage (perfect fill)
        2. Extreme slippage spike (10 pips)
        3. Zero PnL (break even)
        4. Partial fill (represented by small lot size)
        """
        return [
            {
                "ticket": 3001,
                "symbol": "XAUUSD",
                "direction": 1,
                "pnl": 100.0,
                "slippage_pips": 0.0,
                "status": "CLOSED",
            },
            {
                "ticket": 3002,
                "symbol": "XAUUSD",
                "direction": 1,
                "pnl": -500.0,
                "slippage_pips": 10.0,
                "status": "CLOSED",
            },
            {
                "ticket": 3003,
                "symbol": "XAUUSD",
                "direction": 1,
                "pnl": 0.0,
                "slippage_pips": 0.5,
                "status": "CLOSED",
            },
            {
                "ticket": 3004,
                "symbol": "XAUUSD",
                "direction": 1,
                "pnl": 10.0,
                "slippage_pips": 0.2,
                "status": "CLOSED",
                "lot_size": 0.01,
            },
        ]


class ReconciliationScenarioBuilder:
    """
    Populates TradeLogger with deterministic intraday states to test
    risk reconciliation and recovery after restarts.
    """

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def populate_near_daily_loss(
        self, logger: TradeLogger, balance: float = 10000.0, target_loss_pct: float = 0.045
    ) -> None:
        """
        Populates closed losing trades to approach the daily loss limit.
        Default target is 4.5% (system limit is 5%).
        """
        target_loss = balance * target_loss_pct
        # Create 3 losing trades to reach the target loss
        loss_per_trade = target_loss / 3

        for i in range(3):
            ticket = 5000 + i
            logger.log_trade(
                ticket=ticket,
                symbol="XAUUSD",
                direction=1,
                entry_price=2300.0,
                lot_size=0.1,
                status="OPEN",
            )
            # Update to CLOSED with specific loss
            logger.update_trade(ticket=ticket, exit_price=2290.0, pnl=-loss_per_trade)

    def populate_active_losing_streak(self, logger: TradeLogger, count: int = 2) -> None:
        """
        Populates a sequence of consecutive losing trades.
        Default is 2 (system limit is 3).
        """
        for i in range(count):
            ticket = 6000 + i
            logger.log_trade(
                ticket=ticket,
                symbol="XAUUSD",
                direction=1,
                entry_price=2300.0,
                lot_size=0.1,
                status="OPEN",
            )
            logger.update_trade(ticket=ticket, exit_price=2295.0, pnl=-50.0)


class EnsembleScenarioBuilder:
    """
    Generates deterministic signal dictionaries and ensemble states for testing.
    """

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def consensus_signals(
        self, direction: SignalDirection, confidence: float = 0.8
    ) -> dict[str, Signal]:
        """All models agree on a direction."""
        return {
            "ppo": Signal(direction=direction, confidence=confidence),
            "dreamer": Signal(direction=direction, confidence=confidence),
            "lstm": Signal(direction=direction, confidence=confidence),
        }

    def dissent_signals(self) -> dict[str, Signal]:
        """Models have conflicting BUY/SELL directions."""
        return {
            "ppo": Signal(direction=SignalDirection.BUY, confidence=0.8),
            "dreamer": Signal(direction=SignalDirection.SELL, confidence=0.8),
            "lstm": Signal(direction=SignalDirection.HOLD, confidence=0.0),
        }

    def veto_signals(self, direction: SignalDirection) -> dict[str, Signal]:
        """Models agree on direction but one has very low confidence (<0.4)."""
        return {
            "ppo": Signal(direction=direction, confidence=0.9),
            "dreamer": Signal(direction=direction, confidence=0.35),  # Trigger veto
            "lstm": Signal(direction=direction, confidence=0.9),
        }

    def regime_context(self, regime: MarketRegime, transition_score: float = 0.0) -> RegimeInfo:
        """Generates RegimeInfo for adaptive consensus testing."""
        return RegimeInfo(
            label=regime,
            confidence=0.9,
            transition_score=transition_score,
            volatility_index=1.0 if regime != MarketRegime.NEWS_SHOCK else 3.5,
            raw_features={},
        )

    def populate_ensemble_state(
        self,
        ensemble: DynamicEnsemble,
        model_name: str,
        pattern: list[bool],
        confidence: float = 0.8,
    ) -> None:
        """
        Populates DynamicEnsemble history with a specific success/failure pattern.
        pattern: list of booleans (True = Correct, False = Incorrect)
        """
        for is_correct in pattern:
            # We must use record_prediction + record_outcome to populate _history correctly
            pred_dir = SignalDirection.BUY
            actual_dir = SignalDirection.BUY if is_correct else SignalDirection.SELL

            ensemble.record_prediction(model_name, pred_dir, confidence)
            ensemble.record_outcome(model_name, actual_dir)
