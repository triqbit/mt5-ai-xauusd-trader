"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/analytics/execution_quality.py
Execution quality and trade efficiency analytics.
Author : Jules04
License: MIT
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from src.core.trade_logger import ModelSignal, Trade


class TradeExecutionQuality(BaseModel):
    """Execution quality metrics for a single executed trade."""

    ticket: int
    symbol: str
    direction: int
    requested_price: float
    actual_price: float
    slippage_pips: float
    execution_latency_ms: float
    fill_quality: float = Field(..., description="1.0 is perfect fill, lower is worse")
    edge_capture: float = Field(..., description="Spread-adjusted edge captured")
    mfe_pips: float = Field(..., description="Maximum Favorable Excursion")
    mae_pips: float = Field(..., description="Maximum Adverse Excursion")
    post_entry_drift_5m: float = Field(..., description="Price drift 5m after entry")
    post_entry_drift_15m: float = Field(..., description="Price drift 15m after entry")


class BlockedSignalQuality(BaseModel):
    """Opportunity cost metrics for signals blocked by risk management."""

    signal_id: int
    symbol: str
    direction: int
    requested_price: float
    rejection_reason: str
    opportunity_cost_pips: float = Field(..., description="Hypothetical PnL in pips if executed")
    max_favorable_pips: float = Field(..., description="Max hypothetical gain")
    was_correct_rejection: bool = Field(..., description="True if hypothetical trade would have lost")


class ExecutionSummary(BaseModel):
    """Aggregated execution efficiency metrics."""

    total_trades: int
    avg_slippage_pips: float
    avg_latency_ms: float
    avg_fill_quality: float
    total_edge_capture: float
    avg_post_entry_drift_5m: float
    blocked_signals_count: int
    rejection_accuracy: float = Field(..., description="Percentage of correct rejections")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExecutionAnalyzer:
    """
    Institutional-grade execution quality analysis engine.
    Distinguishes alpha quality from execution quality.
    """

    def __init__(self, pip_value: float = 0.1) -> None:
        """
        Initialize the analyzer.

        Args:
            pip_value: Pip value for XAUUSD (default 0.1).
        """
        self.pip_value = pip_value

    def analyze_trade(
        self, trade: Trade, signal: ModelSignal, market_data: pd.DataFrame
    ) -> TradeExecutionQuality:
        """
        Calculate execution quality metrics for an executed trade.

        Args:
            trade: The executed Trade object.
            signal: The original ModelSignal object.
            market_data: High-frequency or M1 market data covering the trade duration.

        Returns:
            TradeExecutionQuality metrics.
        """
        # 1. Slippage calculation (requested vs actual)
        slippage_pips = (trade.entry_price - signal.entry_price) * signal.direction / self.pip_value

        # 2. Latency (signal timestamp vs trade created_at)
        latency_ms = (trade.created_at - signal.timestamp).total_seconds() * 1000

        # 3. Fill quality (1.0 = no slippage, degrades as slippage increases relative to volatility)
        # Using a simple heuristic: 1.0 - (slippage / 10 pips capped at 1.0)
        fill_quality = max(0.0, 1.0 - (abs(slippage_pips) / 10.0))

        # 4. MFE / MAE (Maximum Favorable / Adverse Excursion)
        # Filter market data from trade entry to exit (or now if open)
        exit_time = trade.updated_at if trade.status == "CLOSED" else datetime.now(timezone.utc)
        period_data = market_data[
            (market_data["time"] >= trade.created_at) & (market_data["time"] <= exit_time)
        ]

        if not period_data.empty:
            if trade.direction > 0:  # BUY
                mfe_pips = (period_data["high"].max() - trade.entry_price) / self.pip_value
                mae_pips = (trade.entry_price - period_data["low"].min()) / self.pip_value
            else:  # SELL
                mfe_pips = (trade.entry_price - period_data["low"].min()) / self.pip_value
                mae_pips = (period_data["high"].max() - trade.entry_price) / self.pip_value
        else:
            mfe_pips = mae_pips = 0.0

        # 5. Post-entry drift (5m and 15m)
        drift_5m = self._calculate_drift(trade, market_data, 5)
        drift_15m = self._calculate_drift(trade, market_data, 15)

        # 6. Edge Capture (Spread adjusted)
        # Simplified: (PnL in pips + spread) / (Expected Alpha in pips)
        # Here we just use realized pips as a proxy for capture
        realized_pips = (
            (trade.exit_price - trade.entry_price) * trade.direction / self.pip_value
            if trade.exit_price
            else 0.0
        )
        edge_capture = realized_pips  # Placeholder for more complex spread-adjusted edge

        return TradeExecutionQuality(
            ticket=trade.ticket,
            symbol=trade.symbol,
            direction=trade.direction,
            requested_price=signal.entry_price,
            actual_price=trade.entry_price,
            slippage_pips=slippage_pips,
            execution_latency_ms=latency_ms,
            fill_quality=fill_quality,
            edge_capture=edge_capture,
            mfe_pips=mfe_pips,
            mae_pips=mae_pips,
            post_entry_drift_5m=drift_5m,
            post_entry_drift_15m=drift_15m,
        )

    def analyze_blocked_signal(
        self, signal: ModelSignal, market_data: pd.DataFrame, rejection_reason: str = "Risk"
    ) -> BlockedSignalQuality:
        """
        Calculate opportunity cost for a signal that was blocked by risk management.

        Args:
            signal: The original ModelSignal object.
            market_data: Market data after the signal timestamp.
            rejection_reason: Why the trade was blocked.

        Returns:
            BlockedSignalQuality metrics.
        """
        # Look ahead 4 hours for opportunity cost (or until signal SL/TP would hit)
        lookahead_period = market_data[
            (market_data["time"] > signal.timestamp)
            & (market_data["time"] <= signal.timestamp + pd.Timedelta(hours=4))
        ]

        if not lookahead_period.empty:
            # Hypothetical exit: last price in lookahead or first hit of SL/TP
            # For simplicity, we use the last price in the window
            hypothetical_exit = lookahead_period.iloc[-1]["close"]

            opportunity_cost_pips = (
                (hypothetical_exit - signal.entry_price) * signal.direction / self.pip_value
            )

            if signal.direction > 0:
                max_favorable = (lookahead_period["high"].max() - signal.entry_price) / self.pip_value
            else:
                max_favorable = (signal.entry_price - lookahead_period["low"].min()) / self.pip_value
        else:
            opportunity_cost_pips = 0.0
            max_favorable = 0.0

        was_correct_rejection = opportunity_cost_pips <= 0

        return BlockedSignalQuality(
            signal_id=signal.id,
            symbol=signal.symbol,
            direction=signal.direction,
            requested_price=signal.entry_price,
            rejection_reason=rejection_reason,
            opportunity_cost_pips=opportunity_cost_pips,
            max_favorable_pips=max_favorable,
            was_correct_rejection=was_correct_rejection,
        )

    def get_summary(
        self,
        trades_quality: List[TradeExecutionQuality],
        blocked_quality: List[BlockedSignalQuality],
    ) -> ExecutionSummary:
        """
        Aggregate trade quality metrics into an institutional summary.

        Args:
            trades_quality: List of individual trade quality metrics.
            blocked_quality: List of individual blocked signal quality metrics.

        Returns:
            ExecutionSummary report.
        """
        if not trades_quality:
            return ExecutionSummary(
                total_trades=0,
                avg_slippage_pips=0.0,
                avg_latency_ms=0.0,
                avg_fill_quality=0.0,
                total_edge_capture=0.0,
                avg_post_entry_drift_5m=0.0,
                blocked_signals_count=len(blocked_quality),
                rejection_accuracy=0.0,
            )

        rejection_accuracy = (
            sum(1 for b in blocked_quality if b.was_correct_rejection) / len(blocked_quality)
            if blocked_quality
            else 0.0
        )

        return ExecutionSummary(
            total_trades=len(trades_quality),
            avg_slippage_pips=float(np.mean([t.slippage_pips for t in trades_quality])),
            avg_latency_ms=float(np.mean([t.execution_latency_ms for t in trades_quality])),
            avg_fill_quality=float(np.mean([t.fill_quality for t in trades_quality])),
            total_edge_capture=float(sum([t.edge_capture for t in trades_quality])),
            avg_post_entry_drift_5m=float(np.mean([t.post_entry_drift_5m for t in trades_quality])),
            blocked_signals_count=len(blocked_quality),
            rejection_accuracy=rejection_accuracy,
        )

    def _calculate_drift(self, trade: Trade, market_data: pd.DataFrame, minutes: int) -> float:
        """Calculate price drift over a specific window after entry."""
        drift_time = trade.created_at + pd.Timedelta(minutes=minutes)
        future_data = market_data[
            (market_data["time"] > trade.created_at) & (market_data["time"] <= drift_time)
        ]

        if future_data.empty:
            return 0.0

        last_price = future_data.iloc[-1]["close"]
        drift_pips = (last_price - trade.entry_price) * trade.direction / self.pip_value
        return drift_pips
