"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/utils/synthetic_data.py
Deterministic scenario generator for testing system robustness across market regimes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

import numpy as np
import pandas as pd

from src.core.schemas import TradeSignal


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
        if regime == "mean_reversion":
            return self._generate_mean_reversion(n_steps, start_price, volatility)
        if regime == "low_volatility_drift":
            return self._generate_low_volatility_drift(n_steps, start_price)
        if regime == "news_shock":
            return self._generate_news_shock(n_steps, start_price)
        raise ValueError(f"Unknown regime: {regime}")

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
        returns[-1] = 0.1  # 10% move in one bar
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
        signal.timestamp = sat
        return signal, df, sat

    def drawdown_violation(self, symbol: str = "XAUUSD") -> tuple[TradeSignal, pd.DataFrame, float]:
        """Signal with excessive drawdown (e.g., 0.15)."""
        signal, df = self.passing_buy(symbol)
        return signal, df, 0.15

    def confidence_violation(self, symbol: str = "XAUUSD") -> tuple[TradeSignal, pd.DataFrame]:
        """Signal with confidence below threshold (0.4)."""
        signal, df = self.passing_buy(symbol)
        signal.confidence = 0.4
        return signal, df

    def signal_flicker_violation(self, symbol: str = "XAUUSD") -> list[TradeSignal]:
        """A sequence of oscillating signals (BUY, SELL, BUY, SELL, ...)."""
        signals = []
        base_price = 2300.0
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
                return {"win_rate": 0.3}

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
