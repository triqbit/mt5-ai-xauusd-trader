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
    NEWS_SHOCK = "news_shock"
    FAT_FINGER = "fat_finger"
    BULL_BEAR_TRAP = "bull_bear_trap"
    SHORT_SQUEEZE = "short_squeeze"
    CASCADE_LIQUIDATION = "cascade_liquidation"


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
    bars_per_day: int = Field(288, ge=1, description="Number of bars per trading day (default 5m)")
    start_date: str = Field("2024-01-01", description="Start date for the simulation")
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
    recovery_bars: int = 0
    description: str = ""

    def to_report_summary(self) -> Any:
        """Convert to RareEventSummary for ResearchReporter."""
        from src.research.reporting import RareEventSummary

        return RareEventSummary(
            event_type=self.event_type.value,
            peak_impact_pct=self.peak_impact_pct,
            realized_volatility=self.realized_volatility,
            recovery_attained=self.recovery_attained,
            recovery_bars=self.recovery_bars,
            description=self.description,
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

    def _generate_t_returns(self, n: int, drift: float, vol: float, df: float = 5.0) -> np.ndarray:
        """
        Generate returns following a Student's t-distribution to capture 'fat tails'
        observed in real market data.
        """
        # Variance of standard t-distribution is df / (df - 2) for df > 2
        if df > 2:
            scale = vol * np.sqrt((df - 2) / df)
            return drift + self.rng.standard_t(df, n) * scale
        return drift + self.rng.standard_t(df, n) * vol

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
        if config.event_type == RareEventType.NEWS_SHOCK:
            return self._simulate_news_shock(config)
        if config.event_type == RareEventType.FAT_FINGER:
            return self._simulate_fat_finger(config)
        if config.event_type == RareEventType.BULL_BEAR_TRAP:
            return self._simulate_bull_bear_trap(config)
        if config.event_type == RareEventType.SHORT_SQUEEZE:
            return self._simulate_short_squeeze(config)
        if config.event_type == RareEventType.CASCADE_LIQUIDATION:
            return self._simulate_cascade_liquidation(config)
        raise ValueError(f"Unknown rare event type: {config.event_type}")

    def _generate_base_ohlc(
        self,
        start_price: float,
        returns: np.ndarray,
        base_vol: float,
        base_volume: int,
        gaps: np.ndarray | None = None,
        spread_multiplier: float = 1.0,
        vols: np.ndarray | None = None,
        bars_per_day: int = 288,
        start_date: str = "2024-01-01",
    ) -> pd.DataFrame:
        """
        Helper to convert a returns series into a valid OHLCV DataFrame.
        Ensures price continuity: open[i] = close[i-1] unless gap requested.
        """
        n = len(returns)
        if vols is None:
            vols = np.full(n, base_vol)

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

            # Intraday range scaled by local volatility
            noise = self.rng.rayleigh(vols[i] * opens[i], 2)

            highs[i] = max(opens[i], closes[i]) + noise[0]
            lows[i] = min(opens[i], closes[i]) - noise[1]

            current_price = closes[i]

        # Generate spread: base XAUUSD spread ~0.2-0.4, plus volatility noise
        base_spread = 0.25 * spread_multiplier
        # Spread increases exponentially with local volatility to reflect liquidity drying up
        # Normal vol ~0.0005 -> exp(0.0005 * 500) ~ 1.28
        # High vol ~0.01 -> exp(0.01 * 500) ~ 148 (massive spread widening)
        vol_spread_impact = np.exp(vols * 500) - 1.0
        spreads = base_spread + (self.rng.exponential(vols * 50, n) + vol_spread_impact).astype(np.float32)

        # Volume correlates with absolute returns and volatility
        vol_factor = 1.0 + (np.abs(returns) / (vols + 1e-9)) * 0.5
        adj_volume = np.clip(base_volume * vol_factor, 1, 10000).astype(int)

        # Generate ticks and volumes
        tick_volumes = self.rng.poisson(adj_volume).astype(np.int64)
        real_volumes = self.rng.poisson(adj_volume * 10).astype(np.int64)

        df = pd.DataFrame(
            {
                "open": opens.astype(np.float32),
                "high": highs.astype(np.float32),
                "low": lows.astype(np.float32),
                "close": closes.astype(np.float32),
                "tick_volume": tick_volumes,
                "real_volume": real_volumes,
                "spread": spreads.astype(np.float32),
            }
        )

        # Add a timestamp index. Use freq relative to bars_per_day if possible.
        total_seconds = 24 * 60 * 60
        seconds_per_bar = max(1, total_seconds // bars_per_day)

        df.index = pd.date_range(start=start_date, periods=n, freq=f"{seconds_per_bar}s")
        df.index.name = "time"

        return df

    def _simulate_flash_crash(
        self, config: RareEventConfig
    ) -> tuple[pd.DataFrame, RareEventResult]:
        """
        Simulates a rapid price collapse and partial/full recovery.
        Calibrated to trigger high-volatility regimes.
        """
        n = config.n_steps
        returns = self._generate_t_returns(n, config.drift, config.base_volatility)
        vols = np.full(n, config.base_volatility)

        start_idx = n // 2
        crash_duration = int(10 * config.event_magnitude)
        recovery_duration = int(30 * config.event_magnitude)

        # Ensure impact is significant enough for RegimeDetector thresholds
        impact = -0.05 * config.event_magnitude

        # Crash phase: acceleration
        for i in range(crash_duration):
            idx = start_idx + i
            if idx < n:
                returns[idx] += (impact / crash_duration) * (1 + i / crash_duration)
                # Significant vol boost to trigger NEWS_SHOCK or VOLATILE_BREAKOUT
                vols[idx] *= 4.0 * config.event_magnitude

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
                vols[idx] *= 1.8 * config.event_magnitude

        df = self._generate_base_ohlc(
            config.start_price,
            returns,
            config.base_volatility,
            config.base_volume,
            vols=vols,
            bars_per_day=config.bars_per_day,
            start_date=config.start_date,
        )

        # Volume Surge during crash
        crash_mask = (np.arange(n) >= start_idx) & (np.arange(n) < start_idx + crash_duration)
        df.loc[crash_mask, "tick_volume"] *= np.int64(3 * config.event_magnitude)

        # Peak impact is the max percentage deviation from the price before the crash
        event_prices = df["close"].iloc[start_idx : start_idx + crash_duration + recovery_duration]
        start_price = df["close"].iloc[start_idx - 1] if start_idx > 0 else df["close"].iloc[0]
        deviations = (event_prices / start_price - 1).values
        peak_impact = float(deviations[np.argmax(np.abs(deviations))])

        result = RareEventResult(
            event_type=RareEventType.FLASH_CRASH,
            config=config,
            start_index=start_idx,
            end_index=min(n - 1, start_idx + crash_duration + recovery_duration),
            peak_impact_pct=peak_impact,
            realized_volatility=float(np.std(returns) * np.sqrt(config.bars_per_day)),
            recovery_attained=float(recovered_total_pct / abs(impact)) if impact != 0 else 0,
            recovery_bars=recovery_duration,
            description=f"Flash crash of {peak_impact:.2%} with {config.recovery_factor:.0%} recovery.",
        )

        return df, result

    def _simulate_liquidity_vacuum(
        self, config: RareEventConfig
    ) -> tuple[pd.DataFrame, RareEventResult]:
        """Simulates a period of erratic price jumps and extreme spreads."""
        n = config.n_steps
        returns = self._generate_t_returns(n, config.drift, config.base_volatility)
        vols = np.full(n, config.base_volatility)

        start_idx = n // 3
        duration = int(40 * config.event_magnitude)

        for i in range(duration):
            idx = start_idx + i
            if idx < n:
                # Fat tails via T-distribution with very low degrees of freedom
                returns[idx] = (
                    self.rng.standard_t(df=1.2)
                    * config.base_volatility
                    * 15
                    * config.event_magnitude
                )
                vols[idx] *= 4.0 * config.event_magnitude

        df = self._generate_base_ohlc(
            config.start_price,
            returns,
            config.base_volatility,
            config.base_volume,
            vols=vols,
            bars_per_day=config.bars_per_day,
            start_date=config.start_date,
        )

        vacuum_mask = (np.arange(n) >= start_idx) & (np.arange(n) < start_idx + duration)
        # Volume drops significantly
        df.loc[vacuum_mask, "tick_volume"] = self.rng.integers(
            1, 5, np.sum(vacuum_mask), dtype=np.int64
        )

        # Spreads widen significantly: e.g. for XAUUSD spreads can jump from 0.2 to 2.0+
        spread_mult = np.float32(8.0 * config.event_magnitude)
        df.loc[vacuum_mask, "spread"] *= spread_mult

        # In a vacuum, the range (high-low) is much larger than the open-close move
        # We add extra volatility to the high/low of each candle relative to base volatility
        noise_magnitude = (
            df.loc[vacuum_mask, "open"]
            * np.float32(config.base_volatility * 5.0 * config.event_magnitude)
        ).astype(np.float32)
        df.loc[vacuum_mask, "high"] += noise_magnitude
        df.loc[vacuum_mask, "low"] -= noise_magnitude

        event_prices = df["close"].iloc[start_idx : start_idx + duration]
        start_price = df["close"].iloc[start_idx - 1] if start_idx > 0 else df["close"].iloc[0]
        deviations = (event_prices / start_price - 1).values
        peak_impact = float(deviations[np.argmax(np.abs(deviations))])

        result = RareEventResult(
            event_type=RareEventType.LIQUIDITY_VACUUM,
            config=config,
            start_index=start_idx,
            end_index=start_idx + duration,
            peak_impact_pct=peak_impact,
            realized_volatility=float(np.std(returns) * np.sqrt(config.bars_per_day)),
            recovery_attained=1.0,
            description=f"Liquidity vacuum with extreme spreads and {peak_impact:.2%} peak deviation.",
        )

        return df, result

    def _simulate_gold_gap(self, config: RareEventConfig) -> tuple[pd.DataFrame, RareEventResult]:
        """Simulates discontinuous price jumps."""
        n = config.n_steps
        returns = self._generate_t_returns(n, config.drift, config.base_volatility)
        vols = np.full(n, config.base_volatility)

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
                vols[gap_idx + i] *= vol_boost

        df = self._generate_base_ohlc(
            config.start_price,
            returns,
            config.base_volatility,
            config.base_volume,
            gaps=gaps,
            vols=vols,
            bars_per_day=config.bars_per_day,
            start_date=config.start_date,
        )

        result = RareEventResult(
            event_type=RareEventType.GOLD_GAP,
            config=config,
            start_index=gap_idx,
            end_index=gap_idx + post_gap_duration,
            peak_impact_pct=gap_magnitude_pct,
            realized_volatility=float(np.std(returns) * np.sqrt(config.bars_per_day)),
            recovery_attained=0.0,
            description=f"Discontinuous gold gap of {gap_magnitude_pct:.2%}.",
        )
        return df, result

    def _simulate_violent_reversal(
        self, config: RareEventConfig
    ) -> tuple[pd.DataFrame, RareEventResult]:
        """Simulates a strong trend followed by an abrupt reversal."""
        n = config.n_steps
        returns = self._generate_t_returns(n, config.drift, config.base_volatility)
        vols = np.full(n, config.base_volatility)

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
                vols[idx] *= 2.0 * config.event_magnitude

        df = self._generate_base_ohlc(
            config.start_price,
            returns,
            config.base_volatility,
            config.base_volume,
            vols=vols,
            bars_per_day=config.bars_per_day,
            start_date=config.start_date,
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
            realized_volatility=float(np.std(returns) * np.sqrt(config.bars_per_day)),
            recovery_attained=0.0,
            description=f"Violent trend reversal of {peak_impact:.2%}.",
        )
        return df, result

    def _simulate_dislocation(
        self, config: RareEventConfig
    ) -> tuple[pd.DataFrame, RareEventResult]:
        """Simulates a regime shift."""
        n = config.n_steps
        returns = self._generate_t_returns(n, config.drift, config.base_volatility)
        vols = np.full(n, config.base_volatility)

        dislocation_idx = n // 3

        # Shift
        returns[dislocation_idx] -= 0.03 * config.event_magnitude
        vols[dislocation_idx] *= 5.0 * config.event_magnitude

        # New regime
        new_vol = config.base_volatility * 3.0 * config.event_magnitude
        new_drift = config.drift - 0.0005 * config.event_magnitude

        n_new = n - (dislocation_idx + 1)
        if n_new > 0:
            returns[dislocation_idx + 1 :] = self._generate_t_returns(n_new, new_drift, new_vol)
            vols[dislocation_idx + 1 :] = new_vol

        df = self._generate_base_ohlc(
            config.start_price,
            returns,
            config.base_volatility,
            config.base_volume,
            vols=vols,
            bars_per_day=config.bars_per_day,
            start_date=config.start_date,
        )

        event_prices = df["close"].iloc[dislocation_idx:]
        start_price = (
            df["close"].iloc[dislocation_idx - 1] if dislocation_idx > 0 else df["close"].iloc[0]
        )
        deviations = (event_prices / start_price - 1).values
        peak_impact = float(deviations[np.argmax(np.abs(deviations))])

        result = RareEventResult(
            event_type=RareEventType.DISLOCATION,
            config=config,
            start_index=dislocation_idx,
            end_index=n - 1,
            peak_impact_pct=peak_impact,
            realized_volatility=float(np.std(returns) * np.sqrt(config.bars_per_day)),
            recovery_attained=0.0,
            description=f"Regime dislocation with {peak_impact:.2%} impact and sustained volatility.",
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

        # Generate base returns then scale noise by the volatility cluster
        returns = config.drift + self._generate_t_returns(n, 0.0, 1.0) * vols
        df = self._generate_base_ohlc(
            config.start_price,
            returns,
            config.base_volatility,
            config.base_volume,
            vols=vols,
            bars_per_day=config.bars_per_day,
            start_date=config.start_date,
        )

        # For Vol Cluster, peak impact is the max absolute price deviation from start
        start_idx = shock_indices[0]
        event_prices = df["close"].iloc[start_idx:]
        start_price = df["close"].iloc[start_idx - 1] if start_idx > 0 else df["close"].iloc[0]
        deviations = (event_prices / start_price - 1).values
        peak_impact = float(deviations[np.argmax(np.abs(deviations))])

        result = RareEventResult(
            event_type=RareEventType.VOL_CLUSTER,
            config=config,
            start_index=start_idx,
            end_index=n - 1,
            peak_impact_pct=peak_impact,
            realized_volatility=float(np.std(returns) * np.sqrt(config.bars_per_day)),
            recovery_attained=0.0,
            description=f"Abnormal volatility cluster with {peak_impact:.2%} peak deviation.",
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

    def generate_report_section(
        self, suite_results: dict[str, tuple[pd.DataFrame, RareEventResult]]
    ) -> Any:
        """
        Convert a suite of results into a RareEventSection for ResearchReporter.

        Args:
            suite_results: Dictionary of scenario names to (DataFrame, Result) tuples.

        Returns:
            RareEventSection: Pydantic model for reporting.
        """
        from src.research.reporting import RareEventSection

        summaries = [res.to_report_summary() for _, res in suite_results.values()]

        # Generate automated insights
        critical_events = [s for s in summaries if abs(s.peak_impact_pct) > 0.05]
        long_recoveries = [s for s in summaries if s.recovery_bars > 50]

        insight_msg = (
            f"Evaluated {len(summaries)} rare event scenarios. "
            f"Detected {len(critical_events)} high-impact events (>5% deviation). "
        )

        if critical_events:
            most_severe = min(summaries, key=lambda s: s.peak_impact_pct)
            insight_msg += f"Most severe impact was {most_severe.event_type} at {most_severe.peak_impact_pct:.2%}. "
        else:
            insight_msg += "All events remained within manageable risk bounds. "

        if long_recoveries:
            insight_msg += f"Detected {len(long_recoveries)} events with extended recovery periods (>50 bars)."

        return RareEventSection(scenarios=summaries, insights=insight_msg)

    def _simulate_news_shock(self, config: RareEventConfig) -> tuple[pd.DataFrame, RareEventResult]:
        """
        Simulates a violent directional move (News Shock) followed by sustained
        high volatility and erratic behavior. Designed to trigger NEWS_SHOCK regime.
        """
        n = config.n_steps
        returns = self._generate_t_returns(n, config.drift, config.base_volatility)
        vols = np.full(n, config.base_volatility)

        shock_idx = n // 3
        # Magnitude needs to be high enough to hit ER > 0.7 and ATR Ratio > 2.0
        # XAUUSD often moves 20-40 dollars on major news ($2300 * 0.015 = $34.5)
        shock_magnitude = 0.03 * config.event_magnitude * self.rng.choice([-1, 1])

        # Phase 1: The Shock (multi-bar directional move to keep ER high)
        shock_len = max(1, int(10 * config.event_magnitude))
        for i in range(shock_len):
            idx = shock_idx + i
            if idx < n:
                returns[idx] = (shock_magnitude / shock_len) * self.rng.uniform(0.9, 1.1)
                vols[idx] *= 20.0 * config.event_magnitude

        # Phase 2: Sustained Volatility and erratic follow-through
        shock_duration = int(40 * config.event_magnitude)
        for i in range(shock_len, shock_duration):
            idx = shock_idx + i
            if idx < n:
                # Decay volatility but keep it high to maintain VoV and ATR Ratio
                decay_factor = np.exp(-(i - shock_len) / (30 * config.event_magnitude))
                vols[idx] = config.base_volatility * (
                    1 + 15.0 * config.event_magnitude * decay_factor
                )
                returns[idx] = self._generate_t_returns(1, config.drift, vols[idx], df=1.2)[0]

        df = self._generate_base_ohlc(
            config.start_price,
            returns,
            config.base_volatility,
            config.base_volume,
            vols=vols,
            bars_per_day=config.bars_per_day,
            start_date=config.start_date,
        )

        event_prices = df["close"].iloc[shock_idx : shock_idx + shock_duration]
        start_price_val = df["close"].iloc[shock_idx - 1] if shock_idx > 0 else df["close"].iloc[0]
        deviations = (event_prices / start_price_val - 1).values
        peak_impact = float(deviations[np.argmax(np.abs(deviations))])

        result = RareEventResult(
            event_type=RareEventType.NEWS_SHOCK,
            config=config,
            start_index=shock_idx,
            end_index=min(n - 1, shock_idx + shock_duration),
            peak_impact_pct=peak_impact,
            realized_volatility=float(np.std(returns) * np.sqrt(config.bars_per_day)),
            recovery_attained=0.0,
            description=f"News-driven directional shock of {peak_impact:.2%}.",
        )
        return df, result

    def _simulate_fat_finger(self, config: RareEventConfig) -> tuple[pd.DataFrame, RareEventResult]:
        """
        Simulates an extreme single-tick outlier (wick) that quickly returns to
        the prior price level. Tests stop-loss resilience.
        """
        n = config.n_steps
        returns = self._generate_t_returns(n, config.drift, config.base_volatility)
        vols = np.full(n, config.base_volatility)

        shock_idx = n // 2
        # Massive outlier: 15-30x base volatility in a single candle's range
        shock_direction = self.rng.choice([-1, 1])
        wick_magnitude = 0.03 * config.event_magnitude * shock_direction

        df = self._generate_base_ohlc(
            config.start_price,
            returns,
            config.base_volatility,
            config.base_volume,
            vols=vols,
            bars_per_day=config.bars_per_day,
            start_date=config.start_date,
        )

        # Inject the fat finger into the high/low of a single candle
        # without significantly moving the close (unless it's a huge move)
        target_idx = df.index[shock_idx]
        wick_impact = np.float32(config.start_price * abs(wick_magnitude))
        if shock_direction == 1:
            df.loc[target_idx, "high"] += wick_impact
        else:
            df.loc[target_idx, "low"] -= wick_impact

        # Widened spread during the fat finger candle
        df.loc[target_idx, "spread"] *= np.float32(15.0 * config.event_magnitude)

        result = RareEventResult(
            event_type=RareEventType.FAT_FINGER,
            config=config,
            start_index=shock_idx,
            end_index=shock_idx + 1,
            peak_impact_pct=wick_magnitude,
            realized_volatility=float(np.std(returns) * np.sqrt(config.bars_per_day)),
            recovery_attained=1.0,
            description=f"Fat finger trade causing {wick_magnitude:.2%} outlier wick.",
        )
        return df, result

    def _simulate_bull_bear_trap(
        self, config: RareEventConfig
    ) -> tuple[pd.DataFrame, RareEventResult]:
        """
        Simulates a fake breakout past a consolidation range followed by a
        violent reversal. Tests trend-following strategy robustness.
        """
        n = config.n_steps
        returns = self._generate_t_returns(n, config.drift, config.base_volatility)
        vols = np.full(n, config.base_volatility)

        start_idx = n // 3
        consolidation_len = 30
        breakout_len = 5
        reversal_len = 15

        # Phase 1: Consolidation (Very low vol)
        vols[start_idx : start_idx + consolidation_len] *= 0.3
        returns[start_idx : start_idx + consolidation_len] *= 0.2

        # Phase 2: Breakout (Fake)
        direction = self.rng.choice([-1, 1])
        breakout_idx = start_idx + consolidation_len
        breakout_mag = 0.01 * config.event_magnitude * direction
        for i in range(breakout_len):
            idx = breakout_idx + i
            if idx < n:
                returns[idx] = (breakout_mag / breakout_len) * self.rng.uniform(0.8, 1.2)
                vols[idx] *= 2.0 * config.event_magnitude

        # Phase 3: Violent Reversal (The Trap)
        reversal_idx = breakout_idx + breakout_len
        # Reversal is 2x the breakout magnitude in the opposite direction
        reversal_mag = -2.5 * breakout_mag
        for i in range(reversal_len):
            idx = reversal_idx + i
            if idx < n:
                returns[idx] = (reversal_mag / reversal_len) * self.rng.uniform(0.9, 1.3)
                vols[idx] *= 4.0 * config.event_magnitude

        df = self._generate_base_ohlc(
            config.start_price,
            returns,
            config.base_volatility,
            config.base_volume,
            vols=vols,
            bars_per_day=config.bars_per_day,
            start_date=config.start_date,
        )

        event_prices = df["close"].iloc[breakout_idx : reversal_idx + reversal_len]
        start_price_val = (
            df["close"].iloc[breakout_idx - 1] if breakout_idx > 0 else df["close"].iloc[0]
        )
        deviations = (event_prices / start_price_val - 1).values
        peak_impact = float(deviations[np.argmax(np.abs(deviations))])

        result = RareEventResult(
            event_type=RareEventType.BULL_BEAR_TRAP,
            config=config,
            start_index=breakout_idx,
            end_index=min(n - 1, reversal_idx + reversal_len),
            peak_impact_pct=peak_impact,
            realized_volatility=float(np.std(returns) * np.sqrt(config.bars_per_day)),
            recovery_attained=0.0,
            description=f"{'Bull' if direction == 1 else 'Bear'} trap: {peak_impact:.2%} reversal after breakout.",
        )
        return df, result

    def _simulate_multi_session_dislocation(
        self, config: RareEventConfig
    ) -> tuple[pd.DataFrame, RareEventResult]:
        """Simulates a sequence of regime shifts across multiple sessions."""
        n = config.n_steps
        returns = np.zeros(n)
        vols = np.zeros(n)
        drifts = np.zeros(n)

        # Dynamically determine session boundaries and regime parameters
        num_sessions = self.rng.integers(3, 6)
        session_boundaries = np.sort(
            self.rng.choice(range(10, n - 10), num_sessions - 1, replace=False)
        )
        session_boundaries = np.concatenate(([0], session_boundaries, [n]))

        for i in range(num_sessions):
            start, end = int(session_boundaries[i]), int(session_boundaries[i + 1])

            # Randomize regime characteristics
            vol_mult = self.rng.uniform(1.0, 5.0) * config.event_magnitude
            drift_shift = self.rng.uniform(-0.002, 0.002) * config.event_magnitude

            vol = config.base_volatility * vol_mult
            drift = config.drift + drift_shift

            vols[start:end] = vol
            drifts[start:end] = drift
            returns[start:end] = self._generate_t_returns(end - start, drift, vol)

        df = self._generate_base_ohlc(
            config.start_price,
            returns,
            config.base_volatility,
            config.base_volume,
            vols=vols,
            bars_per_day=config.bars_per_day,
            start_date=config.start_date,
        )

        # Max percentage deviation from the very beginning of the multi-session event
        first_session_end = int(session_boundaries[1])
        event_prices = df["close"].iloc[first_session_end:]
        start_price_val = (
            df["close"].iloc[first_session_end - 1]
            if first_session_end > 0
            else df["close"].iloc[0]
        )
        deviations = (event_prices / start_price_val - 1).values
        peak_impact = float(deviations[np.argmax(np.abs(deviations))])

        result = RareEventResult(
            event_type=RareEventType.MULTI_SESSION_DISLOCATION,
            config=config,
            start_index=first_session_end,
            end_index=n - 1,
            peak_impact_pct=peak_impact,
            realized_volatility=float(np.std(returns) * np.sqrt(config.bars_per_day)),
            recovery_attained=0.0,
            description=f"Multi-session regime dislocation ({num_sessions} sessions) with {peak_impact:.2%} peak deviation.",
        )
        return df, result

    def _simulate_short_squeeze(
        self, config: RareEventConfig
    ) -> tuple[pd.DataFrame, RareEventResult]:
        """
        Simulates a rapid parabolic upward move driven by buy-side liquidation.
        Tests resistance-breakout and stop-loss hunting logic.
        """
        n = config.n_steps
        returns = self._generate_t_returns(n, config.drift, config.base_volatility)
        vols = np.full(n, config.base_volatility)

        squeeze_idx = n // 3
        # Parabolic move: accelerating returns
        squeeze_len = max(1, int(15 * config.event_magnitude))
        total_move = 0.04 * config.event_magnitude

        for i in range(squeeze_len):
            idx = squeeze_idx + i
            if idx < n:
                # Accelerating return: (i+1)^2 / sum(1..len^2)
                accel_factor = (i + 1) ** 2 / ((squeeze_len * (squeeze_len + 1) * (2 * squeeze_len + 1)) / 6)
                returns[idx] = total_move * accel_factor + self.rng.uniform(0, 0.001)
                vols[idx] *= 10.0 * config.event_magnitude

        # Blow-off top and sharp reversal
        reversal_len = int(10 * config.event_magnitude)
        for i in range(reversal_len):
            idx = squeeze_idx + squeeze_len + i
            if idx < n:
                returns[idx] = -0.015 * config.event_magnitude * self.rng.uniform(0.8, 1.2)
                vols[idx] *= 5.0 * config.event_magnitude

        df = self._generate_base_ohlc(
            config.start_price,
            returns,
            config.base_volatility,
            config.base_volume,
            vols=vols,
            bars_per_day=config.bars_per_day,
            start_date=config.start_date,
        )

        event_prices = df["close"].iloc[squeeze_idx : squeeze_idx + squeeze_len + reversal_len]
        start_price_val = df["close"].iloc[squeeze_idx - 1] if squeeze_idx > 0 else df["close"].iloc[0]
        deviations = (event_prices / start_price_val - 1).values
        # For a squeeze, we are interested in the peak price reached
        peak_impact = float(np.max(deviations))

        result = RareEventResult(
            event_type=RareEventType.SHORT_SQUEEZE,
            config=config,
            start_index=squeeze_idx,
            end_index=min(n - 1, squeeze_idx + squeeze_len + reversal_len),
            peak_impact_pct=peak_impact,
            realized_volatility=float(np.std(returns) * np.sqrt(config.bars_per_day)),
            recovery_attained=0.0,
            recovery_bars=reversal_len,
            description=f"Parabolic short squeeze of {peak_impact:.2%} with blow-off top.",
        )
        return df, result

    def _simulate_cascade_liquidation(
        self, config: RareEventConfig
    ) -> tuple[pd.DataFrame, RareEventResult]:
        """
        Simulates a series of accelerating downward price shocks (margin calls).
        Tests trailing-stop and capital preservation logic under extreme stress.
        """
        n = config.n_steps
        returns = self._generate_t_returns(n, config.drift, config.base_volatility)
        vols = np.full(n, config.base_volatility)

        start_idx = n // 4
        # Three distinct waves of liquidation
        waves = 3
        wave_len = int(12 * config.event_magnitude)
        gap_len = int(5 * config.event_magnitude)

        current_idx = start_idx
        for wave in range(waves):
            wave_magnitude = -0.02 * config.event_magnitude * (1 + wave * 0.5)
            for i in range(wave_len):
                if current_idx < n:
                    returns[current_idx] = (wave_magnitude / wave_len) * self.rng.uniform(0.9, 1.4)
                    vols[current_idx] *= (5.0 + wave * 2.0) * config.event_magnitude
                    current_idx += 1

            # Brief pause / feeble bounce
            for i in range(gap_len):
                if current_idx < n:
                    returns[current_idx] = 0.001 * config.event_magnitude * self.rng.uniform(0, 1)
                    vols[current_idx] *= 2.0 * config.event_magnitude
                    current_idx += 1

        df = self._generate_base_ohlc(
            config.start_price,
            returns,
            config.base_volatility,
            config.base_volume,
            vols=vols,
            bars_per_day=config.bars_per_day,
            start_date=config.start_date,
        )

        event_prices = df["close"].iloc[start_idx:current_idx]
        start_price_val = df["close"].iloc[start_idx - 1] if start_idx > 0 else df["close"].iloc[0]
        deviations = (event_prices / start_price_val - 1).values
        # For liquidation, we are interested in the maximum drop
        peak_impact = float(np.min(deviations))

        result = RareEventResult(
            event_type=RareEventType.CASCADE_LIQUIDATION,
            config=config,
            start_index=start_idx,
            end_index=min(n - 1, current_idx),
            peak_impact_pct=peak_impact,
            realized_volatility=float(np.std(returns) * np.sqrt(config.bars_per_day)),
            recovery_attained=0.0,
            recovery_bars=0,
            description=f"Cascade liquidation with {waves} waves of selling and {peak_impact:.2%} peak drop.",
        )
        return df, result
