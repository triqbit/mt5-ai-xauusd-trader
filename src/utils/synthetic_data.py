"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/utils/synthetic_data.py
Deterministic scenario generator for testing system robustness across market regimes.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

from src.core.types import TradeSignal


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
