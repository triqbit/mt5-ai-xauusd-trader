"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/utils/synthetic_data.py
Deterministic scenario generator for testing system robustness across market regimes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import numpy as np
import pandas as pd

from src.core.schemas import TradeSignal


@dataclass
class ValidationScenario:
    """Bundles all inputs required for ExecutionFilter validation."""

    signal: TradeSignal
    market_data: pd.DataFrame
    current_drawdown: float = 0.0
    timestamp: datetime | None = None
    model_health: dict[str, Any] | None = None
    trade_logger: Any | None = None


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
        ] = "ranging",
        start_price: float = 2300.0,
        trend_strength: float = 0.001,
        volatility: float = 0.002,
    ) -> pd.DataFrame:
        """
        Main entry point for data generation.
        """
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
        raise ValueError(f"Unknown regime: {regime}")

    def generate_with_holes(
        self, n_steps: int = 100, hole_pct: float = 0.1, regime: str = "ranging"
    ) -> pd.DataFrame:
        """Generates data and then injects NaNs (holes) to test data quality handling."""
        df = self.generate(n_steps=n_steps, regime=regime)  # type: ignore
        mask = self.rng.random(len(df)) < hole_pct
        # Don't poke a hole in the last row to ensure we always have a current price
        mask[-1] = False
        cols = ["open", "high", "low", "close"]
        for col in cols:
            df.loc[mask, col] = np.nan
        return df

    def generate_stale_feed(self, n_steps: int = 100, stale_len: int = 5) -> pd.DataFrame:
        """Generates data where the last few bars are exact copies (frozen feed)."""
        df = self.generate(n_steps=n_steps, regime="trending")
        last_good_idx = n_steps - stale_len - 1
        last_bar = df.iloc[last_good_idx].copy()
        for i in range(last_good_idx + 1, n_steps):
            df.iloc[i] = last_bar
        return df

    def _generate_base(self, n_steps: int, start_price: float, returns: np.ndarray) -> pd.DataFrame:
        """Helper to convert returns to OHLCV."""
        prices = start_price * np.exp(np.cumsum(returns))

        # Simple OHLC approximation from a single price series
        noise = self.rng.normal(0, 0.0005, (n_steps, 4))
        df = pd.DataFrame(
            {
                "open": prices * (1 + noise[:, 0]),
                "high": prices * (1 + np.abs(noise[:, 1])),
                "low": prices * (1 - np.abs(noise[:, 2])),
                "close": prices,
                "tick_volume": self.rng.integers(100, 1000, n_steps),
            }
        )

        # Ensure high is actually the highest and low is the lowest
        df["high"] = df[["open", "close", "high"]].max(axis=1)
        df["low"] = df[["open", "close", "low"]].min(axis=1)

        # Add a synthetic datetime index
        start_time = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
        df.index = [start_time + timedelta(minutes=5 * i) for i in range(n_steps)]

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

    def _generate_malformed(self, n_steps: int, start_price: float) -> pd.DataFrame:
        df = self._generate_ranging(n_steps, start_price, 0.001)

        # Inject anomalies
        # 1. High < Low
        df.iloc[0, df.columns.get_loc("high")] = df.iloc[0, df.columns.get_loc("low")] - 10.0

        # 2. Negative price
        df.iloc[1, df.columns.get_loc("close")] = -100.0

        # 3. NaNs
        df.iloc[2, df.columns.get_loc("open")] = np.nan

        # 4. Zero volume
        df.iloc[3, df.columns.get_loc("tick_volume")] = 0

        return df


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
                )
            )
        return signals

    def ensemble_dissent(
        self,
        symbol: str = "XAUUSD",
        price: float = 2000.0,
    ) -> list[TradeSignal]:
        """Generates signals representing conflicting model votes."""
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
                )
            )
        return signals

    def drawdown_circuit_breaker(
        self,
        symbol: str = "XAUUSD",
        price: float = 2000.0,
    ) -> list[TradeSignal]:
        """Generates signals for testing the 15% peak-to-valley circuit breaker."""
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
            )
        ]


class ExecutionScenarioBuilder:
    """
    Generates ValidationScenario objects tailored to test specific ExecutionFilter layers.
    """

    def __init__(self, seed: int = 42):
        self.gen = ScenarioGenerator(seed=seed)

    def passing_buy(self, symbol: str = "XAUUSD") -> ValidationScenario:
        """A clean BUY signal in a moderate bullish trend."""
        df = self.gen.generate(n_steps=300, regime="trending", trend_strength=0.0002, volatility=0.0005)
        signal = TradeSignal(
            symbol=symbol,
            direction=1,
            entry_price=df["close"].iloc[-1],
            stop_loss=df["close"].iloc[-1] - 10,
            take_profit=df["close"].iloc[-1] + 20,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=0.8,
        )
        return ValidationScenario(signal=signal, market_data=df)

    def atr_failure(self, symbol: str = "XAUUSD") -> ValidationScenario:
        """Signal during extreme volatility spike (ATR failure)."""
        df = self.gen.generate(n_steps=200, regime="ranging", volatility=0.0005)
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
        return ValidationScenario(signal=signal, market_data=df)

    def trend_failure(self, symbol: str = "XAUUSD") -> ValidationScenario:
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
        return ValidationScenario(signal=signal, market_data=df)

    def ema_out_of_sequence(self, symbol: str = "XAUUSD") -> ValidationScenario:
        """BUY signal where EMAs are not correctly stacked."""
        df = self.gen.generate(n_steps=300, regime="trending", trend_strength=0.0005)
        df["base_M5_ema_8"] = df["close"].ewm(span=8, adjust=False).mean()
        df["base_M5_ema_21"] = df["close"].ewm(span=21, adjust=False).mean()
        df["base_M5_ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
        df["base_M5_ema_200"] = df["close"].ewm(span=200, adjust=False).mean()

        last_idx = df.index[-1]
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
        return ValidationScenario(signal=signal, market_data=df)

    def momentum_failure(self, symbol: str = "XAUUSD") -> ValidationScenario:
        """BUY signal when RSI is too high (overbought)."""
        df = self.gen.generate(n_steps=300, regime="trending", trend_strength=0.0005)
        df_spike = self.gen.generate(n_steps=50, regime="trending", trend_strength=0.01, start_price=df["close"].iloc[-1])
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
        return ValidationScenario(signal=signal, market_data=df)

    def session_violation(self, symbol: str = "XAUUSD") -> ValidationScenario:
        """Signal generated during a Saturday (market closed)."""
        scenario = self.passing_buy(symbol)
        # Force timestamp to a Saturday (2024-01-06 is a Saturday)
        scenario.timestamp = datetime(2024, 1, 6, 12, 0, tzinfo=UTC)
        return scenario

    def drawdown_breach(self, symbol: str = "XAUUSD") -> ValidationScenario:
        """Signal generated when account is in 20% drawdown (>15% limit)."""
        scenario = self.passing_buy(symbol)
        scenario.current_drawdown = 0.20
        return scenario

    def confidence_failure(self, symbol: str = "XAUUSD") -> ValidationScenario:
        """Signal with confidence below typical 0.6 threshold."""
        scenario = self.passing_buy(symbol)
        scenario.signal.confidence = 0.4
        return scenario

    def performance_floor_failure(self, symbol: str = "XAUUSD") -> ValidationScenario:
        """Signal when historical win rate is below 45% floor."""
        scenario = self.passing_buy(symbol)
        # Mock trade_logger with low win rate
        class MockLogger:
            def read_performance_report(self):
                return {"win_rate": 0.35}

        scenario.trade_logger = MockLogger()
        return scenario

    def flicker_sequence(self, symbol: str = "XAUUSD") -> list[ValidationScenario]:
        """Sequence of 5 signals alternating BUY/SELL to trigger Flicker Guard."""
        scenarios = []
        # Use a trending regime so it passes other filters more easily,
        # but we will rely on precomputed metrics in tests to force pass layers 1-9.
        df = self.gen.generate(n_steps=300, regime="trending", trend_strength=0.0002, volatility=0.0005)
        price = df["close"].iloc[-1]

        for i in range(5):
            direction = 1 if i % 2 == 0 else -1
            sl = price - (direction * 10)
            tp = price + (direction * 20)
            signal = TradeSignal(
                symbol=symbol,
                direction=direction,
                entry_price=price,
                stop_loss=sl,
                take_profit=tp,
                lot_size=0.1,
                algorithm="ensemble",
                confidence=0.8,
            )
            scenarios.append(ValidationScenario(signal=signal, market_data=df))
        return scenarios


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
