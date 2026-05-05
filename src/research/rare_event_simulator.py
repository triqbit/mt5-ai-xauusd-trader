"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/rare_event_simulator.py
Generates rare but plausible market situations for black-swan resilience testing.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RareEventType(str, Enum):
    """Types of rare market events to simulate."""

    FLASH_CRASH = "flash_crash"
    LIQUIDITY_VACUUM = "liquidity_vacuum"
    GOLD_GAP = "gold_gap"
    VIOLENT_REVERSAL = "violent_reversal"
    DISLOCATION = "dislocation"
    VOL_CLUSTER = "vol_cluster"
    MULTI_SESSION_DISLOCATION = "multi_session_dislocation"


class RareEventConfig(BaseModel):
    """Configuration for rare event simulation."""

    event_type: RareEventType
    n_steps: int = Field(500, ge=100)
    start_price: float = Field(2300.0, gt=0)
    base_volatility: float = Field(0.0005, gt=0)
    drift: float = Field(0.0, description="Base daily-equivalent drift")
    base_volume: int = Field(500, ge=10)
    event_magnitude: float = Field(1.0, gt=0)  # Multiplier for the severity
    recovery_factor: float = Field(
        0.5, ge=0, le=1.0, description="Proportion of event impact recovered"
    )
    seed: int | None = None


class RareEventResult(BaseModel):
    """Metadata about the generated rare event."""

    event_type: RareEventType
    config: RareEventConfig
    start_index: int
    end_index: int
    peak_impact_pct: float
    realized_volatility: float
    recovery_attained: float

    def to_report_summary(self) -> Any:
        """Convert to RareEventSummary for ResearchReporter."""
        from src.research.reporting import RareEventSummary

        return RareEventSummary(
            event_type=self.event_type.value,
            peak_impact_pct=self.peak_impact_pct,
            realized_volatility=self.realized_volatility,
            recovery_attained=self.recovery_attained,
        )


class RareEventSimulator:
    """
    Generates synthetic market data representing rare but plausible 'black-swan' events.

    Designed to test XAUUSD strategy resilience beyond historical distributions by
    simulating various adversarial market conditions such as flash crashes,
    liquidity vacuums, and regime dislocations.
    """

    def __init__(self, seed: int | None = None):
        """
        Initialize the RareEventSimulator.

        Args:
            seed: Optional random seed for reproducibility.
        """
        self.rng = np.random.default_rng(seed)

    def generate_scenario(self, config: RareEventConfig) -> tuple[pd.DataFrame, RareEventResult]:
        """
        Generates a synthetic OHLCV DataFrame containing the specified rare event.

        Args:
            config: Configuration for the rare event to be simulated.

        Returns:
            A tuple containing:
                - pd.DataFrame: OHLCV data with columns ['open', 'high', 'low', 'close',
                  'tick_volume', 'spread'].
                - RareEventResult: Metadata about the generated event.

        Raises:
            ValueError: If the event_type in config is unknown.
        """
        if config.seed is not None:
            self.rng = np.random.default_rng(config.seed)

        if config.event_type == RareEventType.FLASH_CRASH:
            return self._simulate_flash_crash(config)
        if config.event_type == RareEventType.LIQUIDITY_VACUUM:
            return self._simulate_liquidity_vacuum(config)
        if config.event_type == RareEventType.GOLD_GAP:
            return self._simulate_gold_gap(config)
        if config.event_type == RareEventType.VIOLENT_REVERSAL:
            return self._simulate_violent_reversal(config)
        if config.event_type == RareEventType.DISLOCATION:
            return self._simulate_dislocation(config)
        if config.event_type == RareEventType.VOL_CLUSTER:
            return self._simulate_vol_cluster(config)
        if config.event_type == RareEventType.MULTI_SESSION_DISLOCATION:
            return self._simulate_multi_session_dislocation(config)
        raise ValueError(f"Unknown rare event type: {config.event_type}")

    def _generate_base_ohlc(
        self,
        start_price: float,
        returns: np.ndarray,
        base_vol: float,
        base_volume: int,
        gaps: np.ndarray | None = None,
        spread_multiplier: float = 1.0,
    ) -> pd.DataFrame:
        """
        Helper to convert a returns series into a valid OHLCV DataFrame.
        Ensures price continuity: open[i] = close[i-1] unless gap requested.
        """
        n = len(returns)
        opens = np.zeros(n)
        highs = np.zeros(n)
        lows = np.zeros(n)
        closes = np.zeros(n)

        current_price = start_price
        for i in range(n):
            if gaps is not None and gaps[i] != 0:
                opens[i] = current_price + gaps[i]
            else:
                opens[i] = current_price

            closes[i] = opens[i] * np.exp(returns[i])

            # Intraday range
            # Generate two random deviations for high and low
            # Scale by volatility and the actual move in the bar
            noise = self.rng.rayleigh(base_vol * opens[i], 2)

            highs[i] = max(opens[i], closes[i]) + noise[0]
            lows[i] = min(opens[i], closes[i]) - noise[1]

            current_price = closes[i]

        # Generate spread: base XAUUSD spread ~0.2-0.4, plus volatility noise
        base_spread = 0.25 * spread_multiplier
        spreads = base_spread + self.rng.exponential(base_vol * 100, n)

        df = pd.DataFrame(
            {
                "open": opens,
                "high": highs,
                "low": lows,
                "close": closes,
                "tick_volume": self.rng.poisson(base_volume, n),
                "spread": spreads,
            }
        )

        # Add a dummy timestamp index
        df.index = pd.date_range(start="2024-01-01", periods=n, freq="5min")

        return df

    def _simulate_flash_crash(
        self, config: RareEventConfig
    ) -> tuple[pd.DataFrame, RareEventResult]:
        """Simulates a rapid price collapse and partial/full recovery."""
        n = config.n_steps
        returns = self.rng.normal(config.drift, config.base_volatility, n)

        start_idx = n // 2
        crash_duration = int(10 * config.event_magnitude)
        recovery_duration = int(30 * config.event_magnitude)

        impact = -0.04 * config.event_magnitude

        # Crash phase: acceleration
        for i in range(crash_duration):
            idx = start_idx + i
            if idx < n:
                returns[idx] += (impact / crash_duration) * (1 + i / crash_duration)

        # Recovery phase
        recovered_total_pct = 0.0
        recovery_per_step = (
            (-impact * config.recovery_factor / recovery_duration) if recovery_duration > 0 else 0
        )
        for i in range(recovery_duration):
            idx = start_idx + crash_duration + i
            if idx < n:
                step_recovery = recovery_per_step * self.rng.uniform(0.5, 1.5)
                returns[idx] += step_recovery
                recovered_total_pct += step_recovery

        df = self._generate_base_ohlc(
            config.start_price, returns, config.base_volatility, config.base_volume
        )

        # Volume Surge during crash
        crash_mask = (np.arange(n) >= start_idx) & (np.arange(n) < start_idx + crash_duration)
        df.loc[crash_mask, "tick_volume"] *= int(3 * config.event_magnitude)

        # Peak impact is the max percentage deviation from the price before the crash
        event_prices = df["close"].iloc[start_idx : start_idx + crash_duration + recovery_duration]
        start_price = df["close"].iloc[start_idx - 1] if start_idx > 0 else df["close"].iloc[0]
        peak_impact = float((event_prices / start_price - 1).min())

        result = RareEventResult(
            event_type=RareEventType.FLASH_CRASH,
            config=config,
            start_index=start_idx,
            end_index=min(n - 1, start_idx + crash_duration + recovery_duration),
            peak_impact_pct=peak_impact,
            realized_volatility=float(np.std(returns) * np.sqrt(288)),
            recovery_attained=float(recovered_total_pct / abs(impact)) if impact != 0 else 0,
        )

        return df, result

    def _simulate_liquidity_vacuum(
        self, config: RareEventConfig
    ) -> tuple[pd.DataFrame, RareEventResult]:
        """Simulates a period of erratic price jumps and extreme spreads."""
        n = config.n_steps
        returns = self.rng.normal(config.drift, config.base_volatility, n)

        start_idx = n // 3
        duration = int(40 * config.event_magnitude)

        for i in range(duration):
            idx = start_idx + i
            if idx < n:
                # Fat tails via T-distribution
                returns[idx] = (
                    self.rng.standard_t(df=1.5)
                    * config.base_volatility
                    * 12
                    * config.event_magnitude
                )

        df = self._generate_base_ohlc(
            config.start_price, returns, config.base_volatility, config.base_volume
        )

        vacuum_mask = (np.arange(n) >= start_idx) & (np.arange(n) < start_idx + duration)
        # Volume drops significantly
        df.loc[vacuum_mask, "tick_volume"] = self.rng.integers(1, 5, np.sum(vacuum_mask))

        # Spreads widen significantly: e.g. for XAUUSD spreads can jump from 0.2 to 2.0+
        df.loc[vacuum_mask, "spread"] *= 8.0 * config.event_magnitude

        # In a vacuum, the range (high-low) is much larger than the open-close move
        # We add extra volatility to the high/low of each candle relative to base volatility
        noise_magnitude = df.loc[vacuum_mask, "open"] * config.base_volatility * 5.0 * config.event_magnitude
        df.loc[vacuum_mask, "high"] += noise_magnitude
        df.loc[vacuum_mask, "low"] -= noise_magnitude

        event_prices = df["close"].iloc[start_idx : start_idx + duration]
        start_price = df["close"].iloc[start_idx - 1] if start_idx > 0 else df["close"].iloc[0]
        peak_impact = float(np.max(np.abs(event_prices / start_price - 1)))

        result = RareEventResult(
            event_type=RareEventType.LIQUIDITY_VACUUM,
            config=config,
            start_index=start_idx,
            end_index=start_idx + duration,
            peak_impact_pct=peak_impact,
            realized_volatility=float(np.std(returns) * np.sqrt(288)),
            recovery_attained=1.0,
        )

        return df, result

    def _simulate_gold_gap(self, config: RareEventConfig) -> tuple[pd.DataFrame, RareEventResult]:
        """Simulates discontinuous price jumps."""
        n = config.n_steps
        returns = self.rng.normal(config.drift, config.base_volatility, n)

        gap_idx = n // 2
        gap_magnitude_pct = 0.02 * config.event_magnitude * self.rng.choice([-1, 1])

        gaps = np.zeros(n)
        gaps[gap_idx] = config.start_price * gap_magnitude_pct

        # Follow-through volatility
        vol_boost = 4.0 * config.event_magnitude
        post_gap_duration = 20
        for i in range(post_gap_duration):
            if gap_idx + i < n:
                returns[gap_idx + i] *= vol_boost

        df = self._generate_base_ohlc(
            config.start_price, returns, config.base_volatility, config.base_volume, gaps=gaps
        )

        result = RareEventResult(
            event_type=RareEventType.GOLD_GAP,
            config=config,
            start_index=gap_idx,
            end_index=gap_idx + post_gap_duration,
            peak_impact_pct=gap_magnitude_pct,
            realized_volatility=float(np.std(returns) * np.sqrt(288)),
            recovery_attained=0.0,
        )
        return df, result

    def _simulate_violent_reversal(
        self, config: RareEventConfig
    ) -> tuple[pd.DataFrame, RareEventResult]:
        """Simulates a strong trend followed by an abrupt reversal."""
        n = config.n_steps
        returns = self.rng.normal(config.drift, config.base_volatility, n)

        start_idx = n // 5
        trend_duration = n // 4
        reversal_idx = start_idx + trend_duration
        reversal_duration = int(30 * config.event_magnitude)

        # Phase 1: Trend
        returns[start_idx:reversal_idx] += 0.002 * config.event_magnitude

        # Phase 2: Reversal
        for i in range(reversal_duration):
            idx = reversal_idx + i
            if idx < n:
                returns[idx] -= 0.004 * config.event_magnitude * (1 + i / 15)

        df = self._generate_base_ohlc(
            config.start_price, returns, config.base_volatility, config.base_volume
        )

        # Peak impact is the reversal magnitude from the peak reached during the trend
        peak_price = df["high"].iloc[start_idx:reversal_idx].max()
        min_price_after = df["low"].iloc[reversal_idx : reversal_idx + reversal_duration].min()
        peak_impact = float(min_price_after / peak_price - 1)

        result = RareEventResult(
            event_type=RareEventType.VIOLENT_REVERSAL,
            config=config,
            start_index=reversal_idx,
            end_index=min(n - 1, reversal_idx + reversal_duration),
            peak_impact_pct=peak_impact,
            realized_volatility=float(np.std(returns) * np.sqrt(288)),
            recovery_attained=0.0,
        )
        return df, result

    def _simulate_dislocation(
        self, config: RareEventConfig
    ) -> tuple[pd.DataFrame, RareEventResult]:
        """Simulates a regime shift."""
        n = config.n_steps
        returns = self.rng.normal(config.drift, config.base_volatility, n)

        dislocation_idx = n // 3

        # Shift
        returns[dislocation_idx] -= 0.03 * config.event_magnitude

        # New regime
        new_vol = config.base_volatility * 3.0 * config.event_magnitude
        new_drift = config.drift - 0.0005 * config.event_magnitude

        for i in range(dislocation_idx + 1, n):
            returns[i] = self.rng.normal(new_drift, new_vol)

        df = self._generate_base_ohlc(
            config.start_price, returns, config.base_volatility, config.base_volume
        )

        event_prices = df["close"].iloc[dislocation_idx:]
        start_price = df["close"].iloc[dislocation_idx - 1] if dislocation_idx > 0 else df["close"].iloc[0]
        peak_impact = float((event_prices / start_price - 1).min())

        result = RareEventResult(
            event_type=RareEventType.DISLOCATION,
            config=config,
            start_index=dislocation_idx,
            end_index=n - 1,
            peak_impact_pct=peak_impact,
            realized_volatility=float(np.std(returns) * np.sqrt(288)),
            recovery_attained=0.0,
        )
        return df, result

    def _simulate_vol_cluster(
        self, config: RareEventConfig
    ) -> tuple[pd.DataFrame, RareEventResult]:
        """Simulates an abnormal cluster of high volatility with multiple shocks."""
        n = config.n_steps
        vols = np.full(n, config.base_volatility)

        shock_indices = [n // 4, n // 2, 3 * n // 4]

        alpha = 0.2
        beta = 0.75

        current_vol = config.base_volatility
        for i in range(shock_indices[0], n):
            shock = 0
            if i in shock_indices:
                # Multiple decaying shocks
                multiplier = 1.0 if i == shock_indices[0] else 0.5
                shock = 0.02 * config.event_magnitude * multiplier

            # GARCH(1,1) approximation
            current_vol = np.sqrt(
                config.base_volatility**2 * (1 - alpha - beta)
                + alpha * shock**2
                + beta * current_vol**2
            )
            vols[i] = current_vol

        returns = self.rng.normal(config.drift, vols, n)
        df = self._generate_base_ohlc(
            config.start_price, returns, config.base_volatility, config.base_volume
        )

        # For Vol Cluster, peak impact is the max absolute price deviation from start
        start_idx = shock_indices[0]
        event_prices = df["close"].iloc[start_idx:]
        start_price = df["close"].iloc[start_idx - 1] if start_idx > 0 else df["close"].iloc[0]
        peak_impact = float(np.max(np.abs(event_prices / start_price - 1)))

        result = RareEventResult(
            event_type=RareEventType.VOL_CLUSTER,
            config=config,
            start_index=start_idx,
            end_index=n - 1,
            peak_impact_pct=peak_impact,
            realized_volatility=float(np.std(returns) * np.sqrt(288)),
            recovery_attained=0.0,
        )
        return df, result

    def generate_suite(
        self, n_steps: int = 500, magnitude: float = 1.0, seed: int | None = None
    ) -> dict[str, tuple[pd.DataFrame, RareEventResult]]:
        """Generates a standard suite of all rare event scenarios."""
        suite = {}
        for event_type in RareEventType:
            config = RareEventConfig(
                event_type=event_type,
                n_steps=n_steps,
                event_magnitude=magnitude,
                seed=seed if seed is None else seed + list(RareEventType).index(event_type),
            )
            suite[event_type.value] = self.generate_scenario(config)
        return suite

    def _simulate_multi_session_dislocation(
        self, config: RareEventConfig
    ) -> tuple[pd.DataFrame, RareEventResult]:
        """Simulates a sequence of regime shifts across multiple sessions."""
        n = config.n_steps
        returns = np.zeros(n)
        vols = np.zeros(n)
        drifts = np.zeros(n)

        # Divide into 4 sessions
        session_size = n // 4
        regimes = [
            {"vol": config.base_volatility, "drift": config.drift},
            {
                "vol": config.base_volatility * 3.0 * config.event_magnitude,
                "drift": config.drift - 0.001 * config.event_magnitude,
            },
            {
                "vol": config.base_volatility * 1.5 * config.event_magnitude,
                "drift": config.drift + 0.0005 * config.event_magnitude,
            },
            {
                "vol": config.base_volatility * 5.0 * config.event_magnitude,
                "drift": config.drift - 0.002 * config.event_magnitude,
            },
        ]

        for i in range(4):
            start = i * session_size
            end = (i + 1) * session_size if i < 3 else n
            vols[start:end] = regimes[i]["vol"]
            drifts[start:end] = regimes[i]["drift"]
            returns[start:end] = self.rng.normal(drifts[start:end], vols[start:end])

        df = self._generate_base_ohlc(
            config.start_price, returns, config.base_volatility, config.base_volume
        )

        # Max percentage deviation from the very beginning of the multi-session event
        event_prices = df["close"].iloc[session_size:]
        start_price_val = df["close"].iloc[session_size - 1] if session_size > 0 else df["close"].iloc[0]
        peak_impact = float(np.max(np.abs(event_prices / start_price_val - 1)))

        result = RareEventResult(
            event_type=RareEventType.MULTI_SESSION_DISLOCATION,
            config=config,
            start_index=session_size,
            end_index=n - 1,
            peak_impact_pct=peak_impact,
            realized_volatility=float(np.std(returns) * np.sqrt(288)),
            recovery_attained=0.0,
        )
        return df, result
