"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/analytics/execution_quality.py
Institutional-grade execution analytics to measure efficiency and trade quality.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class FillQuality(BaseModel):
    """Assessment of fill quality relative to market conditions."""

    score: float = Field(
        ..., ge=0.0, le=1.0, description="Quality score from 0.0 (poor) to 1.0 (perfect)"
    )
    slippage_vs_spread: float = Field(
        ..., description="Ratio of slippage to spread at time of execution"
    )
    is_favorable: bool = Field(
        ..., description="True if execution price was better than or equal to signal price"
    )


class ExecutionMetrics(BaseModel):
    """Detailed metrics for a single trade execution."""

    ticket: int
    symbol: str
    direction: int
    signal_price: float
    execution_price: float
    slippage_raw: float
    slippage_pips: float
    latency_ms: float
    fill_quality: FillQuality
    edge_capture: float = Field(..., description="Spread-adjusted edge capture metric")


class BlockedTradeQuality(BaseModel):
    """Analysis of signals that were rejected by risk management."""

    signal_id: int
    symbol: str
    reason: str
    signal_price: float
    direction: int
    opportunity_cost: float = Field(
        ..., description="Potential PnL lost (in pips) by not taking the trade"
    )
    post_signal_drift: Dict[str, float] = Field(
        default_factory=dict, description="Price drift at intervals (e.g. '5m', '15m')"
    )


class PostEntryDrift(BaseModel):
    """Analysis of price movement after trade entry."""

    ticket: int
    drift_metrics: Dict[str, float] = Field(
        ..., description="PnL drift in pips at fixed intervals after entry"
    )


class TradeQualityReport(BaseModel):
    """Aggregated report for institutional trade evaluation."""

    ticket: int
    execution: ExecutionMetrics
    drift: Optional[PostEntryDrift] = None
    overall_score: float = Field(..., ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExecutionAnalyzer:
    """
    Analyzes execution efficiency and trade quality.
    Distinguishes alpha quality from execution quality and raises institutional evaluation standards.
    """

    def __init__(self, pip_size: float = 0.01):
        """
        Initialize the analyzer.
        :param pip_size: The size of one pip for the asset (default 0.01 for XAUUSD).
        """
        self.pip_size = pip_size
        self.logger = logging.getLogger(__name__)

    def analyze_execution(
        self,
        ticket: int,
        symbol: str,
        direction: int,
        signal_price: float,
        execution_price: float,
        signal_time: datetime,
        execution_time: datetime,
        spread: float,
    ) -> ExecutionMetrics:
        """
        Calculates execution slippage, latency, and fill quality.

        :param ticket: Trade ticket ID.
        :param symbol: Trading symbol.
        :param direction: 1 for BUY, -1 for SELL.
        :param signal_price: Price at which the AI generated the signal.
        :param execution_price: Actual price at which the trade was filled.
        :param signal_time: Timestamp when signal was generated.
        :param execution_time: Timestamp when trade was executed.
        :param spread: Market spread at the time of execution.
        :return: ExecutionMetrics object.
        """
        # Slippage: favorable if positive (better price than signal)
        # For BUY (1): slippage = signal_price - execution_price
        # For SELL (-1): slippage = execution_price - signal_price
        slippage_raw = (signal_price - execution_price) * direction
        slippage_pips = slippage_raw / self.pip_size

        # Latency
        latency_ms = (execution_time - signal_time).total_seconds() * 1000.0

        # Fill Quality
        spread_pips = spread / self.pip_size
        if slippage_pips >= 0:
            fill_score = 1.0
        else:
            # Penalty based on how much of the spread the slippage consumes.
            # If slippage is more than 2x spread, score becomes 0.
            fill_score = max(0.0, 1.0 - (abs(slippage_pips) / max(spread_pips * 2, 0.1)))

        fill_quality = FillQuality(
            score=round(fill_score, 4),
            slippage_vs_spread=round(slippage_pips / max(spread_pips, 0.1), 4),
            is_favorable=slippage_raw >= 0,
        )

        # Edge Capture: Ratio of retained edge after execution costs.
        # Simple version: capture = 1.0 - (slippage_cost / spread) if slippage is negative.
        edge_capture = (
            max(0.0, 1.0 + (slippage_pips / max(spread_pips, 0.1)))
            if slippage_pips < 0
            else 1.0
        )

        return ExecutionMetrics(
            ticket=ticket,
            symbol=symbol,
            direction=direction,
            signal_price=signal_price,
            execution_price=execution_price,
            slippage_raw=round(slippage_raw, 5),
            slippage_pips=round(slippage_pips, 2),
            latency_ms=round(latency_ms, 2),
            fill_quality=fill_quality,
            edge_capture=round(edge_capture, 4),
        )

    def calculate_post_entry_drift(
        self,
        ticket: int,
        entry_price: float,
        direction: int,
        future_prices: List[Tuple[datetime, float]],
        entry_time: datetime,
        intervals_minutes: Optional[List[int]] = None,
    ) -> PostEntryDrift:
        """
        Measures price movement at specific intervals after trade entry.
        Helps determine if entries were well-timed (positive drift is good).

        :param ticket: Trade ticket ID.
        :param entry_price: Price at entry.
        :param direction: 1 for BUY, -1 for SELL.
        :param future_prices: List of (timestamp, price) tuples after entry.
        :param entry_time: Timestamp of entry.
        :param intervals_minutes: List of minute offsets to check (default [5, 15, 30, 60]).
        :return: PostEntryDrift object.
        """
        if intervals_minutes is None:
            intervals_minutes = [5, 15, 30, 60]

        drift_metrics = {}

        for interval in intervals_minutes:
            target_time = entry_time + timedelta(minutes=interval)
            # Find closest price in future_prices (within 2-minute window)
            closest_price = None
            min_diff = float("inf")

            for p_time, p_val in future_prices:
                diff = abs((p_time - target_time).total_seconds())
                if diff < min_diff and diff <= 120:
                    min_diff = diff
                    closest_price = p_val

            if closest_price is not None:
                # Drift in pips: (future_price - entry_price) * direction
                drift = (closest_price - entry_price) * direction / self.pip_size
                drift_metrics[f"{interval}m"] = round(drift, 2)

        return PostEntryDrift(ticket=ticket, drift_metrics=drift_metrics)

    def analyze_blocked_trade(
        self,
        signal_id: int,
        symbol: str,
        reason: str,
        direction: int,
        signal_price: float,
        signal_time: datetime,
        future_prices: List[Tuple[datetime, float]],
    ) -> BlockedTradeQuality:
        """
        Analyzes the quality of a signal that was blocked by risk management.
        Calculates opportunity cost based on subsequent price action.

        :param signal_id: ID of the blocked signal.
        :param symbol: Trading symbol.
        :param reason: Reason for rejection.
        :param direction: 1 for BUY, -1 for SELL.
        :param signal_price: Price at signal generation.
        :param signal_time: Timestamp of signal.
        :param future_prices: List of (timestamp, price) tuples after signal.
        :return: BlockedTradeQuality object.
        """
        post_drift = {}
        max_favorable_drift = 0.0

        for interval in [5, 15, 30, 60]:
            target_time = signal_time + timedelta(minutes=interval)
            closest_price = None
            min_diff = float("inf")

            for p_time, p_val in future_prices:
                diff = abs((p_time - target_time).total_seconds())
                if diff < min_diff and diff <= 120:
                    min_diff = diff
                    closest_price = p_val

            if closest_price is not None:
                drift = (closest_price - signal_price) * direction / self.pip_size
                post_drift[f"{interval}m"] = round(drift, 2)
                max_favorable_drift = max(max_favorable_drift, drift)

        return BlockedTradeQuality(
            signal_id=signal_id,
            symbol=symbol,
            reason=reason,
            signal_price=signal_price,
            direction=direction,
            opportunity_cost=round(max_favorable_drift, 2),
            post_signal_drift=post_drift,
        )

    def generate_quality_report(
        self, execution: ExecutionMetrics, drift: Optional[PostEntryDrift] = None
    ) -> TradeQualityReport:
        """
        Combines execution and drift metrics into a single quality report.

        :param execution: Execution metrics.
        :param drift: Post-entry drift metrics (optional).
        :return: TradeQualityReport object.
        """
        # Weighting for overall score: 60% fill quality, 40% timing (drift)
        exec_score = execution.fill_quality.score

        drift_score = 0.5  # Neutral default
        if drift and drift.drift_metrics:
            # Average drift across all intervals, normalized.
            # Simple normalization: 10 pips avg drift is "good" (1.0), -10 is "bad" (0.0)
            avg_drift = sum(drift.drift_metrics.values()) / len(drift.drift_metrics)
            drift_score = max(0.0, min(1.0, 0.5 + (avg_drift / 20.0)))

        overall_score = (exec_score * 0.6) + (drift_score * 0.4)

        return TradeQualityReport(
            ticket=execution.ticket,
            execution=execution,
            drift=drift,
            overall_score=round(overall_score, 4),
        )
